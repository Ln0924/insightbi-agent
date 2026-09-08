class InsightBIError(Exception):
    code = "INSIGHTBI_ERROR"


class ClarificationRequired(InsightBIError):
    code = "CLARIFICATION_REQUIRED"


class PermissionDenied(InsightBIError):
    code = "PERMISSION_DENIED"


class UnsafeSqlError(InsightBIError):
    code = "UNSAFE_SQL"


class QueryExecutionError(InsightBIError):
    code = "QUERY_EXECUTION_ERROR"


class BudgetExceeded(InsightBIError):
    code = "BUDGET_EXCEEDED"

