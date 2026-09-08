from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.core.errors import BudgetExceeded, ClarificationRequired, PermissionDenied, UnsafeSqlError
from app.core.models import QueryMode, QueryResponse, TaskStatus, TraceEvent, UserContext
from app.db.session import engine
from app.llm.runtime import LLMRuntime
from app.observability.metrics import QUERY_LATENCY, QUERY_TOTAL, SQL_GUARD_REJECTED
from app.observability.tracing import trace_store
from app.retrieval.metric_store import MetricStore
from app.retrieval.schema_linker import SchemaLinker
from app.services.analyzer import ResultAnalyzer
from app.services.intent import IntentClassifier
from app.services.planner import AnalysisPlanner
from app.sql.executor import ReadOnlyExecutor
from app.sql.generator import SqlGenerator
from app.sql.guard import SqlGuard


class InsightBIOrchestrator:
    ALLOWED_TABLES: ClassVar[set[str]] = {"sales_fact", "dim_product", "dim_region"}

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.intent = IntentClassifier()
        self.metric_store = MetricStore()
        self.schema_linker = SchemaLinker()
        self.planner = AnalysisPlanner()
        self.generator = SqlGenerator()
        self.guard = SqlGuard(self.settings.sql_max_rows)
        self.executor = ReadOnlyExecutor(engine, self.settings.sql_timeout_seconds, self.settings.sql_max_rows)
        self.analyzer = ResultAnalyzer()
        self.llm = LLMRuntime(self.settings) if self.settings.llm_provider == "openai_compatible" else None
        self.parallel = ThreadPoolExecutor(max_workers=4, thread_name_prefix="semantic-retrieval")

    def _emit(self, trace_id: str, node: str, event: str, **payload) -> None:
        trace_store.emit(TraceEvent(trace_id=trace_id, node=node, event=event, payload=payload))

    def _semantic_retrieve(self, question: str, trace_id: str):
        metric_future = self.parallel.submit(self.metric_store.search, question)
        schema_future = self.parallel.submit(self.schema_linker.link, question)
        metrics, schema = metric_future.result(), schema_future.result()
        tables = list(dict.fromkeys(c.table for c in schema[:5]))
        joins = self.schema_linker.find_join_path(tables)
        self._emit(trace_id, "semantic_retrieval", "completed", metrics=[m.name for m in metrics], schema=[f"{c.table}.{c.column}" for c in schema], join_paths=joins)
        return metrics, schema, [joins] if joins else []

    def _authorize(self, user: UserContext) -> None:
        if "finance" not in user.allowed_domains:
            raise PermissionDenied("当前用户没有财务主题域访问权限")

    def _execute_step(self, question, intent, metrics, schema, step, trace_id, seen_hashes):
        artifact = (
            self.llm.generate_sql(question, step, metrics, schema)
            if self.llm
            else self.generator.generate(question, intent, metrics, step)
        )
        digest = hashlib.sha256(artifact.sql.encode()).hexdigest()
        if digest in seen_hashes:
            raise BudgetExceeded("检测到重复 SQL，已停止无效重试")
        seen_hashes.add(digest)
        guard = self.guard.validate(artifact.sql, UserContext(user_id="system", tenant_id="system"), self.ALLOWED_TABLES)
        if not guard.allowed:
            for violation in guard.violations:
                SQL_GUARD_REJECTED.labels(reason=violation[:32]).inc()
            raise UnsafeSqlError("；".join(guard.violations))
        cost = self.executor.explain_cost(guard.normalized_sql, artifact.parameters)
        if cost > self.settings.sql_cost_limit:
            raise UnsafeSqlError(f"查询计划成本 {cost} 超过阈值")
        self._emit(trace_id, "sql_guard", "accepted", step_id=step.step_id, cost=cost, sql=guard.normalized_sql)
        evidence = self.executor.execute(guard.normalized_sql, artifact.parameters, step.step_id)
        self._emit(trace_id, "sql_executor", "completed", step_id=step.step_id, evidence_id=evidence.evidence_id, row_count=evidence.row_count)
        return evidence

    def run(self, question: str, user: UserContext, trace_id: str | None = None) -> QueryResponse:
        started = time.perf_counter()
        trace_id = trace_id or f"tr_{uuid4().hex}"
        warnings: list[str] = []
        self._emit(trace_id, "request", "accepted", question=question, tenant_id=user.tenant_id, user_id=user.user_id)
        try:
            self._authorize(user)
            intent = self.llm.classify(question) if self.llm else self.intent.classify(question)
            requested_region = intent.filters.get("region_name")
            if user.allowed_regions and requested_region and requested_region not in user.allowed_regions:
                raise PermissionDenied(f"当前用户无权访问区域：{requested_region}")
            if len(user.allowed_regions) == 1 and not requested_region:
                intent.filters["region_name"] = user.allowed_regions[0]
            self._emit(trace_id, "intent", "completed", **intent.model_dump(mode="json"))
            if intent.mode == QueryMode.CLARIFY:
                raise ClarificationRequired("请补充要查询的业务指标、时间范围或分析维度。")
            metrics, schema, join_paths = self._semantic_retrieve(question, trace_id)
            _ = join_paths
            seen_hashes: set[str] = set()
            evidence = []
            sql_statements = []
            if intent.mode == QueryMode.SIMPLE:
                step = self.planner.create_plan(question).steps[0].model_copy(update={"step_id": "query", "question": question})
                item = self._execute_step(question, intent, metrics, schema, step, trace_id, seen_hashes)
                evidence.append(item)
                sql_statements.append(item.sql)
                answer, charts = self.analyzer.simple_answer(item)
            else:
                plan = self.llm.plan(question, metrics, schema) if self.llm else self.planner.create_plan(question)
                self._emit(trace_id, "planner", "created", plan=plan.model_dump(mode="json"))
                if len(plan.steps) > self.settings.max_agent_steps:
                    raise BudgetExceeded("执行计划超过最大步骤预算")
                for step in plan.steps:
                    if any(dep not in {e.step_id for e in evidence} for dep in step.depends_on):
                        raise BudgetExceeded(f"步骤 {step.step_id} 的依赖证据不完整")
                    item = self._execute_step(question, intent, metrics, schema, step, trace_id, seen_hashes)
                    evidence.append(item)
                    sql_statements.append(item.sql)
                if self.llm:
                    report = self.llm.report(question, evidence)
                    answer, charts = report.answer, report.charts
                else:
                    answer, charts = self.analyzer.analysis_report(evidence)
            latency_ms = int((time.perf_counter() - started) * 1000)
            response = QueryResponse(trace_id=trace_id, status=TaskStatus.SUCCEEDED, mode=intent.mode, answer=answer, sql=sql_statements, evidence=evidence, charts=charts, warnings=warnings, latency_ms=latency_ms)
            QUERY_TOTAL.labels(mode=intent.mode, status="succeeded").inc()
            QUERY_LATENCY.labels(mode=intent.mode).observe(latency_ms / 1000)
            self._emit(trace_id, "response", "completed", latency_ms=latency_ms)
            return response
        except ClarificationRequired as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            QUERY_TOTAL.labels(mode="clarify", status="partial").inc()
            return QueryResponse(trace_id=trace_id, status=TaskStatus.PARTIAL, mode=QueryMode.CLARIFY, answer=str(exc), latency_ms=latency_ms)
