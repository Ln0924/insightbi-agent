from app.core.models import AnalysisPlan, PlanStep


class AnalysisPlanner:
    def create_plan(self, question: str) -> AnalysisPlan:
        steps = [
            PlanStep(step_id="trend", title="确认利润趋势", question="按月份查询收入、成本、毛利润和毛利率", success_condition="至少返回两个连续月份的利润指标"),
            PlanStep(step_id="product", title="定位产品贡献", question="按月份和产品查询收入、成本与毛利润", depends_on=["trend"], success_condition="得到各产品利润变化与贡献"),
            PlanStep(step_id="driver", title="拆解业务驱动", question="按产品查询销量、收入、成本和毛利润用于量价本分析", depends_on=["product"], success_condition="能区分销量、售价或单位成本影响"),
        ]
        return AnalysisPlan(objective=question, steps=steps, max_steps=len(steps))
