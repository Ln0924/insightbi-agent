from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class QueryMode(StrEnum):
    SIMPLE = "simple"
    ANALYSIS = "analysis"
    CLARIFY = "clarify"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class UserContext(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=lambda: ["finance", "sales"])
    allowed_regions: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: str | None = None
    idempotency_key: str | None = None
    stream: bool = False


class IntentResult(BaseModel):
    mode: QueryMode
    intent: str
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    time_range: str | None = None
    confidence: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    name: str
    aliases: list[str]
    description: str
    formula: str
    grain: str
    owner: str
    version: str
    dimensions: list[str]
    forbidden_aggregations: list[str] = Field(default_factory=list)


class SchemaCandidate(BaseModel):
    table: str
    column: str
    data_type: str
    description: str
    score: float
    sensitivity: Literal["public", "internal", "sensitive"] = "internal"


class RetrievalBundle(BaseModel):
    metrics: list[MetricDefinition] = Field(default_factory=list)
    schema_candidates: list[SchemaCandidate] = Field(default_factory=list)
    join_paths: list[list[str]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    step_id: str
    title: str
    question: str
    depends_on: list[str] = Field(default_factory=list)
    success_condition: str
    status: TaskStatus = TaskStatus.PENDING
    sql: str | None = None
    evidence_id: str | None = None


class AnalysisPlan(BaseModel):
    objective: str
    steps: list[PlanStep]
    max_steps: int = 10


class SqlArtifact(BaseModel):
    sql: str
    dialect: str = "sqlite"
    tables: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class GuardResult(BaseModel):
    allowed: bool
    normalized_sql: str | None = None
    violations: list[str] = Field(default_factory=list)
    estimated_cost: float | None = None


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid4().hex[:12]}")
    step_id: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    summary: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChartSpec(BaseModel):
    type: Literal["line", "bar", "pie", "table", "kpi"]
    title: str
    x_field: str | None = None
    y_fields: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)


class QueryResponse(BaseModel):
    trace_id: str
    status: TaskStatus
    mode: QueryMode
    answer: str
    sql: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    charts: list[ChartSpec] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latency_ms: int


class AsyncTaskView(BaseModel):
    task_id: str
    status: TaskStatus
    trace_id: str | None = None
    result: QueryResponse | None = None
    error: str | None = None


class TraceEvent(BaseModel):
    trace_id: str
    node: str
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
