from app.retrieval.metric_store import MetricStore
from app.retrieval.schema_linker import SchemaLinker


def test_metric_recall_contains_profit():
    names = [item.name for item in MetricStore().search("毛利润为什么下降", 3)]
    assert "毛利润" in names


def test_schema_linking_and_join_path():
    linker = SchemaLinker()
    candidates = linker.link("按产品分析销售收入", 8)
    assert any(c.column == "revenue" for c in candidates)
    assert linker.find_join_path(["sales_fact", "dim_product"])

