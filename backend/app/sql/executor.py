from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from sqlalchemy import Engine, text

from app.core.errors import QueryExecutionError
from app.core.models import Evidence


class ReadOnlyExecutor:
    def __init__(self, engine: Engine, timeout_seconds: int = 8, max_rows: int = 1000):
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows
        self.pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sql-readonly")

    def explain_cost(self, sql: str, parameters: dict | None = None) -> float:
        with self.engine.connect() as conn:
            plan = conn.execute(text(f"EXPLAIN QUERY PLAN {sql}"), parameters or {}).fetchall()
        scans = sum("SCAN" in " ".join(map(str, row)).upper() for row in plan)
        searches = sum("SEARCH" in " ".join(map(str, row)).upper() for row in plan)
        return scans * 1000 + searches * 100 + len(plan)

    def _run(self, sql: str, parameters: dict) -> tuple[list[str], list[dict]]:
        started = time.perf_counter()
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), parameters)
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result.fetchmany(self.max_rows)]
        _ = time.perf_counter() - started
        return columns, rows

    def execute(self, sql: str, parameters: dict, step_id: str) -> Evidence:
        future = self.pool.submit(self._run, sql, parameters)
        try:
            columns, rows = future.result(timeout=self.timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            raise QueryExecutionError(f"SQL 执行超过 {self.timeout_seconds} 秒") from exc
        except Exception as exc:
            raise QueryExecutionError(str(exc)) from exc
        digest = hashlib.sha256((sql + repr(parameters)).encode()).hexdigest()[:12]
        summary = f"查询返回 {len(rows)} 行，字段：{', '.join(columns)}"
        return Evidence(evidence_id=f"ev_{digest}", step_id=step_id, sql=sql, columns=columns, rows=rows, row_count=len(rows), summary=summary)

