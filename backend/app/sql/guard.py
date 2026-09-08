from __future__ import annotations

import re
from typing import ClassVar

import sqlglot
from sqlglot import exp

from app.core.models import GuardResult, UserContext


class SqlGuard:
    FORBIDDEN_NODES = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create, exp.Command)
    SYSTEM_SCHEMAS: ClassVar[set[str]] = {"information_schema", "mysql", "pg_catalog", "sys"}

    def __init__(self, max_rows: int = 1000):
        self.max_rows = max_rows

    def validate(self, sql: str, user: UserContext, allowed_tables: set[str]) -> GuardResult:
        violations: list[str] = []
        try:
            statements = sqlglot.parse(sql, read="sqlite")
        except sqlglot.errors.ParseError as exc:
            return GuardResult(allowed=False, violations=[f"SQL 语法解析失败：{exc}"])
        if len(statements) != 1:
            violations.append("仅允许单条 SQL")
        expression = statements[0]
        if not isinstance(expression, (exp.Select, exp.Union, exp.Subquery)):
            violations.append("仅允许只读 SELECT 查询")
        if any(expression.find(node) for node in self.FORBIDDEN_NODES):
            violations.append("检测到写入或 DDL 操作")
        referenced = {table.name for table in expression.find_all(exp.Table)}
        unauthorized = referenced - allowed_tables
        if unauthorized:
            violations.append(f"访问未授权表：{', '.join(sorted(unauthorized))}")
        if any(schema in sql.lower() for schema in self.SYSTEM_SCHEMAS):
            violations.append("禁止访问系统库")
        if re.search(r"\b(sleep|benchmark|load_file|outfile|dumpfile)\s*\(", sql, re.IGNORECASE):
            violations.append("检测到高风险函数")
        normalized = expression.sql(dialect="sqlite")
        if isinstance(expression, (exp.Select, exp.Union)) and not expression.args.get("limit"):
            expression = expression.limit(self.max_rows)
            normalized = expression.sql(dialect="sqlite")
        return GuardResult(allowed=not violations, normalized_sql=normalized, violations=violations)
