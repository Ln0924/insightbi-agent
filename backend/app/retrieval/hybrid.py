from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[\u4e00-\u9fff]", text.lower())
    bigrams = ["".join(words[i : i + 2]) for i in range(max(0, len(words) - 1))]
    return words + bigrams


@dataclass
class SearchDocument(Generic[T]):
    doc_id: str
    text: str
    payload: T


class HybridRetriever(Generic[T]):
    """无外部服务也能运行的混合检索器；生产环境可替换为 ES + 向量库。"""

    def __init__(self, documents: list[SearchDocument[T]]):
        self.documents = documents
        self.tokens = {d.doc_id: tokenize(d.text) for d in documents}
        self.df = Counter(token for ts in self.tokens.values() for token in set(ts))

    def _bm25(self, query: list[str], doc_id: str) -> float:
        tokens = self.tokens[doc_id]
        counts = Counter(tokens)
        score = 0.0
        avg_len = sum(map(len, self.tokens.values())) / max(len(self.tokens), 1)
        for token in query:
            df = self.df[token]
            idf = math.log(1 + (len(self.documents) - df + 0.5) / (df + 0.5))
            tf = counts[token]
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(tokens) / max(avg_len, 1)))
        return score

    def _dense_like(self, query: list[str], doc_id: str) -> float:
        q, d = Counter(query), Counter(self.tokens[doc_id])
        dot = sum(q[k] * d[k] for k in q)
        denom = math.sqrt(sum(v * v for v in q.values()) * sum(v * v for v in d.values()))
        return dot / denom if denom else 0.0

    def search(self, query: str, top_k: int = 5) -> list[tuple[T, float]]:
        query_tokens = tokenize(query)
        bm = sorted(self.documents, key=lambda d: self._bm25(query_tokens, d.doc_id), reverse=True)
        dense = sorted(self.documents, key=lambda d: self._dense_like(query_tokens, d.doc_id), reverse=True)
        ranks: dict[str, float] = Counter()
        for result in (bm, dense):
            for rank, doc in enumerate(result[: max(top_k * 2, 10)], 1):
                ranks[doc.doc_id] += 1 / (60 + rank)
        by_id = {d.doc_id: d for d in self.documents}
        output = sorted(ranks.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [(by_id[doc_id].payload, score) for doc_id, score in output]

