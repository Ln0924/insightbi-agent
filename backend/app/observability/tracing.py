from __future__ import annotations

import logging
from collections import defaultdict
from threading import Lock

from app.core.models import TraceEvent

logger = logging.getLogger("insightbi.trace")


class TraceStore:
    """开发环境内存实现；生产环境使用 PostgreSQL/OTel Exporter。"""

    def __init__(self) -> None:
        self._events: dict[str, list[TraceEvent]] = defaultdict(list)
        self._lock = Lock()

    def emit(self, event: TraceEvent) -> None:
        with self._lock:
            self._events[event.trace_id].append(event)
        logger.info("trace_id=%s node=%s event=%s", event.trace_id, event.node, event.event)

    def get(self, trace_id: str) -> list[TraceEvent]:
        return list(self._events.get(trace_id, []))


trace_store = TraceStore()

