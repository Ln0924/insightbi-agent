from __future__ import annotations

import json
from threading import Lock

from redis.exceptions import RedisError

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


class RedisIdempotencyStore:
    """跨实例幂等状态；创建操作依赖 Redis SET NX 保证原子性。"""

    def __init__(self, client, ttl_seconds: int = 3600):
        self.client = client
        self.ttl = ttl_seconds
        self.fallback = IdempotencyStore()

    def _key(self, key: str) -> str:
        return f"idempotency:{key}"

    def begin(self, key: str) -> str:
        redis_key = self._key(key)
        try:
            created = self.client.set(redis_key, "running", ex=self.ttl, nx=True)
        except RedisError:
            return self.fallback.begin(key)
        if created:
            return "created"
        value = self.client.get(redis_key)
        if value == "running" and self.fallback.get(key):
            return "completed"
        return "completed" if value and value != "running" else "running"

    def complete(self, key: str, response: QueryResponse) -> None:
        try:
            self.client.setex(self._key(key), self.ttl, response.model_dump_json())
        except RedisError:
            self.fallback.complete(key, response)

    def fail(self, key: str) -> None:
        try:
            self.client.delete(self._key(key))
        except RedisError:
            self.fallback.fail(key)

    def get(self, key: str) -> QueryResponse | None:
        try:
            value = self.client.get(self._key(key))
        except RedisError:
            return self.fallback.get(key)
        if not value or value == "running":
            return self.fallback.get(key)
        try:
            return QueryResponse.model_validate(json.loads(value))
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
