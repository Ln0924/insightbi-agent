from app.core.models import UserContext
from app.sql.guard import SqlGuard

USER = UserContext(user_id="u1", tenant_id="t1")
TABLES = {"sales_fact", "dim_product", "dim_region"}


def test_accepts_select_and_injects_limit():
    result = SqlGuard(100).validate("SELECT month, SUM(revenue) FROM sales_fact GROUP BY month", USER, TABLES)
    assert result.allowed
    assert "LIMIT 100" in result.normalized_sql


def test_rejects_write_and_unknown_table():
    assert not SqlGuard().validate("DELETE FROM sales_fact", USER, TABLES).allowed
    assert not SqlGuard().validate("SELECT * FROM payroll", USER, TABLES).allowed


def test_rejects_multiple_statements():
    result = SqlGuard().validate("SELECT 1; SELECT 2", USER, TABLES)
    assert not result.allowed

