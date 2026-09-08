from prometheus_client import Counter, Histogram

QUERY_TOTAL = Counter("insightbi_query_total", "查询总数", ["mode", "status"])
QUERY_LATENCY = Histogram("insightbi_query_latency_seconds", "端到端查询延迟", ["mode"])
SQL_GUARD_REJECTED = Counter("insightbi_sql_guard_rejected_total", "SQL Guard 拦截数", ["reason"])
LLM_CALLS = Counter("insightbi_llm_calls_total", "模型调用次数", ["model", "purpose"])

