from __future__ import annotations

import json
import logging
import time
from threading import Lock
from typing import Any

from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ResilientCache:
    """Redis 优先、本地短期缓存回退；Redis 故障不会绕过数据库权限校验。"""

    def __init__(self, redis_client=None, fallback_ttl: int = 30):
        self.redis = redis_client
        self.fallback_ttl = fallback_ttl
        self.local: dict[str, tuple[float, Any]] = {}
        self.lock = Lock()

    def get(self, key: str):
        if self.redis:
            try:
                value = self.redis.get(key)
                if value:
                    return json.loads(value)
            except (RedisError, ValueError, TypeError) as exc:
                logger.warning("Redis cache read failed; using local fallback: %s", exc)
        with self.lock:
            item = self.local.get(key)
            if item and item[0] > time.time():
                return item[1]
            self.local.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if self.redis:
            try:
                self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
                return
            except (RedisError, ValueError, TypeError) as exc:
                logger.warning("Redis cache write failed; using local fallback: %s", exc)
        with self.lock:
            self.local[key] = (time.time() + min(ttl, self.fallback_ttl), value)
