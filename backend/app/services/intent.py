import re

from app.core.models import IntentResult, QueryMode


class IntentClassifier:
    ANALYSIS_WORDS = ("为什么", "原因", "归因", "异常", "下降", "上涨", "影响", "贡献")
    METRICS = ("毛利率", "毛利润", "利润", "收入", "成本", "销量")
    DIMENSIONS = ("产品", "区域", "月份", "类别")

    def classify(self, question: str) -> IntentResult:
        metrics = [word for word in self.METRICS if word in question]
        dimensions = [word for word in self.DIMENSIONS if word in question]
        analysis_hits = [word for word in self.ANALYSIS_WORDS if word in question]
        mode = QueryMode.ANALYSIS if analysis_hits else QueryMode.SIMPLE
        time_range = None
        if match := re.search(r"最近([一二三四五六七八九十\d]+)个?月", question):
            time_range = f"最近{match.group(1)}个月"
        filters = {}
        for region in ("华东", "华南", "华北"):
            if region in question:
                filters["region_name"] = region
        confidence = 0.93 if metrics else 0.62
        if not metrics and not any(x in question for x in ("销售", "经营", "业绩")):
            mode = QueryMode.CLARIFY
        return IntentResult(
            mode=mode,
            intent="business_analysis" if mode == QueryMode.ANALYSIS else "data_query",
            metrics=metrics or ["毛利润"], dimensions=dimensions, filters=filters,
            time_range=time_range, confidence=confidence,
            reasons=[f"命中分析信号：{','.join(analysis_hits)}"] if analysis_hits else ["单指标查询，无中间证据依赖"],
        )

