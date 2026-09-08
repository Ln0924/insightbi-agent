from __future__ import annotations

from threading import Lock

from app.core.models import QueryResponse


class IdempotencyStore:
    def __init__(self) -> None:
        self._responses: dict[str, QueryResponse] = {}
        self._running: set[str] = set()
        self._lock = Lock()

    def begin(self, key: str) -> str:
        with self._lock:
            if key in self._responses:
                return "completed"
            if key in self._running:
                return "running"
            self._running.add(key)
            return "created"

    def complete(self, key: str, response: QueryResponse) -> None:
        with self._lock:
            self._running.discard(key)
            self._responses[key] = response

    def fail(self, key: str) -> None:
        with self._lock:
            self._running.discard(key)

    def get(self, key: str) -> QueryResponse | None:
        return self._responses.get(key)


idempotency_store = IdempotencyStore()

