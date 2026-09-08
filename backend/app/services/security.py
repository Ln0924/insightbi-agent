from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from threading import Lock

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.models import UserContext


class AuthService:
    algorithm = "HS256"

    def decode(self, token: str) -> UserContext:
        settings = get_settings()
        if settings.app_env != "production" and token == "demo-token":
            return UserContext(user_id="demo", tenant_id="demo-company", roles=["analyst"])
        try:
            claims = jwt.decode(token, settings.app_secret_key, algorithms=[self.algorithm])
            return UserContext(
                user_id=claims["sub"], tenant_id=claims["tenant_id"],
                roles=claims.get("roles", []), allowed_domains=claims.get("allowed_domains", []),
                allowed_regions=claims.get("allowed_regions", []),
            )
        except (JWTError, KeyError) as exc:
            raise ValueError("无效或过期的访问令牌") from exc


def make_idempotency_key(question: str, user: UserContext, session_id: str | None, metric_version: str = "v2", schema_version: str = "v1") -> str:
    source = "|".join([user.tenant_id, user.user_id, ",".join(sorted(user.roles)), question.strip(), session_id or "", metric_version, schema_version])
    return hashlib.sha256(source.encode()).hexdigest()


class SlidingWindowRateLimiter:
    """单实例回退实现；生产环境由 Redis Lua 脚本保证多实例原子限流。"""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self.entries: dict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.time()
        with self.lock:
            bucket = self.entries[key]
            while bucket and bucket[0] <= now - self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False, max(1, int(bucket[0] + self.window - now))
            bucket.append(now)
            return True, 0


class RedisSlidingWindowRateLimiter:
    """使用有序集合和 Lua 脚本实现跨实例原子滑动窗口限流。"""

    SCRIPT = """
    local key, now, window, limit, member = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3]), ARGV[4]
    redis.call('ZREMRANGEBYSCORE', key, 0, now-window)
    local count = redis.call('ZCARD', key)
    if count >= limit then
      local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
      return {0, math.max(1, math.ceil((tonumber(oldest[2]) + window - now) / 1000))}
    end
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    return {1, 0}
    """

    def __init__(self, client, limit: int, window_seconds: int = 60):
        self.client = client
        self.limit = limit
        self.window_ms = window_seconds * 1000

    def allow(self, key: str) -> tuple[bool, int]:
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}:{time.perf_counter_ns()}"
        allowed, retry_after = self.client.eval(
            self.SCRIPT, 1, f"rate:{key}", now_ms, self.window_ms, self.limit, member
        )
        return bool(allowed), int(retry_after)
