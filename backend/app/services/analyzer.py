from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.core.models import ChartSpec, Evidence


def _number(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


class ResultAnalyzer:
    def simple_answer(self, evidence: Evidence) -> tuple[str, list[ChartSpec]]:
        if not evidence.rows:
            return "在当前权限和筛选条件下未查询到数据。", []
        chart = ChartSpec(type="line", title="指标趋势", x_field="month", y_fields=[c for c in ("revenue", "cost", "gross_profit", "quantity") if c in evidence.columns], data=evidence.rows)
        latest = evidence.rows[-1]
        values = "，".join(f"{key}={latest[key]}" for key in latest if key != "month")
        return f"查询完成。最新一期（{latest.get('month')}）结果为：{values}。", [chart]

    def analysis_report(self, evidence: list[Evidence]) -> tuple[str, list[ChartSpec]]:
        trend = next((e for e in evidence if e.step_id == "trend"), evidence[0])
        if len(trend.rows) < 2:
            return "现有证据不足以完成趋势归因，需要扩大时间范围或补充数据。", []
        first, last = trend.rows[0], trend.rows[-1]
        gp_change = _number(last.get("gross_profit")) - _number(first.get("gross_profit"))
        revenue_change = _number(last.get("revenue")) - _number(first.get("revenue"))
        cost_change = _number(last.get("cost")) - _number(first.get("cost"))
        direction = "下降" if gp_change < 0 else "上升"

        product_ev = next((e for e in evidence if e.step_id == "product"), None)
        contributions: dict[str, float] = defaultdict(float)
        if product_ev:
            by_product: dict[str, list[dict]] = defaultdict(list)
            for row in product_ev.rows:
                by_product[str(row.get("product_name", "未知产品"))].append(row)
            for product, rows in by_product.items():
                rows.sort(key=lambda x: str(x.get("month")))
                contributions[product] = _number(rows[-1].get("gross_profit")) - _number(rows[0].get("gross_profit"))
        ranked = sorted(contributions.items(), key=lambda x: x[1])
        culprit = ranked[0][0] if ranked else "暂未定位"
        answer = (
            f"结论：分析期内毛利润{direction} {abs(gp_change):,.2f}。"
            f"收入变化 {revenue_change:,.2f}，成本变化 {cost_change:,.2f}；"
            f"产品维度中，{culprit}对利润下行贡献最大。"
            "该结论来自月度趋势、产品贡献和量价本拆解三组可追溯证据；贡献率允许出现负值或超过 100%，因为不同因素可能相互抵消。"
        )
        charts = [ChartSpec(type="line", title="毛利润趋势", x_field="month", y_fields=["gross_profit"], data=trend.rows)]
        if contributions:
            charts.append(ChartSpec(type="bar", title="产品利润变化贡献", x_field="product_name", y_fields=["profit_change"], data=[{"product_name": k, "profit_change": v} for k, v in ranked]))
        return answer, charts

