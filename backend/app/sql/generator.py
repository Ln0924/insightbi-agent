from __future__ import annotations

from app.core.models import IntentResult, MetricDefinition, PlanStep, SqlArtifact


class SqlGenerator:
    """根据受控语义上下文生成 SQL。模型生成器可通过相同接口接入。"""

    def generate(
        self,
        question: str,
        intent: IntentResult,
        metrics: list[MetricDefinition],
        step: PlanStep | None = None,
    ) -> SqlArtifact:
        target = step.question if step else question
        needs_product = any(word in target for word in ("产品", "贡献", "原因", "归因"))
        needs_region = "区域" in target or "region_name" in intent.filters
        group_fields = ["sf.month"]
        select_fields = ["sf.month AS month"]
        joins: list[str] = []
        if needs_product:
            joins.append("JOIN dim_product p ON sf.product_id = p.product_id")
            group_fields.append("p.product_name")
            select_fields.append("p.product_name")
        if needs_region:
            joins.append("JOIN dim_region r ON sf.region_id = r.region_id")
            group_fields.append("r.region_name")
            select_fields.append("r.region_name")

        if any(x in target for x in ("销量", "数量")):
            select_fields.append("SUM(sf.quantity) AS quantity")
        if any(x in target for x in ("收入", "营收", "销售额")):
            select_fields.append("ROUND(SUM(sf.revenue), 2) AS revenue")
        if "成本" in target:
            select_fields.append("ROUND(SUM(sf.cost), 2) AS cost")
        if not any(alias in " ".join(select_fields) for alias in ("revenue", "cost", "gross_profit", "margin_rate", "quantity")) or any(x in target for x in ("利润", "毛利", "原因", "归因", "下降")):
            select_fields.extend([
                "ROUND(SUM(sf.revenue), 2) AS revenue",
                "ROUND(SUM(sf.cost), 2) AS cost",
                "ROUND(SUM(sf.revenue) - SUM(sf.cost), 2) AS gross_profit",
                "ROUND((SUM(sf.revenue)-SUM(sf.cost))*1.0/NULLIF(SUM(sf.revenue),0), 4) AS margin_rate",
            ])
        select_fields = list(dict.fromkeys(select_fields))
        where = ["sf.month >= date((SELECT MAX(month) FROM sales_fact), '-3 months')"]
        parameters = {}
        if region := intent.filters.get("region_name"):
            where.append("r.region_name = :region_name")
            parameters["region_name"] = region
        sql = (
            "SELECT " + ", ".join(select_fields)
            + " FROM sales_fact sf " + " ".join(joins)
            + " WHERE " + " AND ".join(where)
            + " GROUP BY " + ", ".join(group_fields)
            + " ORDER BY sf.month ASC"
        )
        tables = ["sales_fact"]
        if needs_product:
            tables.append("dim_product")
        if needs_region:
            tables.append("dim_region")
        return SqlArtifact(
            sql=sql, tables=tables,
            parameters=parameters, rationale="只使用语义层召回的指标口径、字段与 Join 关系生成查询",
        )
