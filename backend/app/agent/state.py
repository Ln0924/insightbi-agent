from __future__ import annotations

from typing import TypedDict

from app.core.models import (
    AnalysisPlan,
    ChartSpec,
    Evidence,
    IntentResult,
    MetricDefinition,
    SchemaCandidate,
    UserContext,
)


class AgentState(TypedDict, total=False):
    trace_id: str
    question: str
    user: UserContext
    intent: IntentResult
    metrics: list[MetricDefinition]
    schema: list[SchemaCandidate]
    join_paths: list[list[str]]
    plan: AnalysisPlan
    evidence: list[Evidence]
    sql: list[str]
    answer: str
    charts: list[ChartSpec]
    warnings: list[str]
    retries: dict[str, int]
    executed_sql_hashes: set[str]

