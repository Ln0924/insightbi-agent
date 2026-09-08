from app.core.models import MetricDefinition
from app.retrieval.hybrid import HybridRetriever, SearchDocument

METRICS = [
    MetricDefinition(name="营业收入", aliases=["收入", "销售额", "营收"], description="扣除退货后的销售收入", formula="SUM(sales_fact.revenue)", grain="月-产品-区域", owner="财务中心", version="v1.2", dimensions=["月份", "产品", "区域"]),
    MetricDefinition(name="销售成本", aliases=["成本", "主营业务成本"], description="已销售产品对应成本", formula="SUM(sales_fact.cost)", grain="月-产品-区域", owner="财务中心", version="v1.1", dimensions=["月份", "产品", "区域"]),
    MetricDefinition(name="毛利润", aliases=["毛利", "销售毛利", "利润"], description="营业收入减销售成本", formula="SUM(sales_fact.revenue)-SUM(sales_fact.cost)", grain="月-产品-区域", owner="财务中心", version="v2.0", dimensions=["月份", "产品", "区域"]),
    MetricDefinition(name="毛利率", aliases=["利润率"], description="毛利润占营业收入比例，先汇总后相除", formula="(SUM(sales_fact.revenue)-SUM(sales_fact.cost))/NULLIF(SUM(sales_fact.revenue),0)", grain="月-产品-区域", owner="财务中心", version="v2.0", dimensions=["月份", "产品", "区域"], forbidden_aggregations=["AVG(row_margin_rate)"]),
    MetricDefinition(name="销量", aliases=["销售数量", "件数"], description="完成销售的产品数量", formula="SUM(sales_fact.quantity)", grain="月-产品-区域", owner="销售中心", version="v1.0", dimensions=["月份", "产品", "区域"]),
]


class MetricStore:
    def __init__(self) -> None:
        docs = [SearchDocument(m.name, " ".join([m.name, *m.aliases, m.description, *m.dimensions]), m) for m in METRICS]
        self.retriever = HybridRetriever(docs)

    def search(self, question: str, top_k: int = 3) -> list[MetricDefinition]:
        return [metric for metric, _ in self.retriever.search(question, top_k)]

