from collections import deque

from app.core.models import SchemaCandidate
from app.retrieval.hybrid import HybridRetriever, SearchDocument

SCHEMA = [
    SchemaCandidate(table="sales_fact", column="month", data_type="date", description="销售发生月份 自然月", score=0),
    SchemaCandidate(table="sales_fact", column="revenue", data_type="decimal", description="营业收入 销售额 营收", score=0, sensitivity="sensitive"),
    SchemaCandidate(table="sales_fact", column="cost", data_type="decimal", description="销售成本 主营业务成本", score=0, sensitivity="sensitive"),
    SchemaCandidate(table="sales_fact", column="quantity", data_type="integer", description="销量 销售数量 件数", score=0),
    SchemaCandidate(table="sales_fact", column="product_id", data_type="integer", description="产品关联键", score=0),
    SchemaCandidate(table="sales_fact", column="region_id", data_type="integer", description="区域关联键", score=0),
    SchemaCandidate(table="dim_product", column="product_name", data_type="text", description="产品名称 型号", score=0),
    SchemaCandidate(table="dim_product", column="category", data_type="text", description="产品类别", score=0),
    SchemaCandidate(table="dim_region", column="region_name", data_type="text", description="销售区域 华东 华南 华北", score=0),
]

JOINS = {
    "sales_fact": [("dim_product", "sales_fact.product_id = dim_product.product_id"), ("dim_region", "sales_fact.region_id = dim_region.region_id")],
    "dim_product": [("sales_fact", "sales_fact.product_id = dim_product.product_id")],
    "dim_region": [("sales_fact", "sales_fact.region_id = dim_region.region_id")],
}


class SchemaLinker:
    def __init__(self) -> None:
        docs = [SearchDocument(f"{c.table}.{c.column}", f"{c.table} {c.column} {c.description}", c) for c in SCHEMA]
        self.retriever = HybridRetriever(docs)

    def link(self, question: str, top_k: int = 8) -> list[SchemaCandidate]:
        candidates = []
        for candidate, score in self.retriever.search(question, top_k):
            candidates.append(candidate.model_copy(update={"score": round(score, 6)}))
        return candidates

    def find_join_path(self, tables: list[str]) -> list[str]:
        targets = set(tables)
        if len(targets) <= 1:
            return []
        start = next(iter(targets))
        queue = deque([(start, [], {start})])
        while queue:
            current, edges, visited = queue.popleft()
            if targets.issubset(visited):
                return edges
            for neighbor, condition in JOINS.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, [*edges, condition], {*visited, neighbor}))
        return []

