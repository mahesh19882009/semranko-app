"""Distributed rate limiting with a bounded in-process fallback."""

import logging
import time
from collections import defaultdict
from functools import wraps
from threading import Lock
from typing import Callable, Optional

from fastapi import HTTPException, Request
from redis import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryRateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def consume(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window
        with self._lock:
            active = [stamp for stamp in self._buckets[key] if stamp > cutoff]
            if len(active) >= limit:
                self._buckets[key] = active
                return False, max(1, int(active[0] + window - now))
            active.append(now)
            self._buckets[key] = active
            return True, window

    def clear(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Backward-compatible helper used by existing abuse regression tests."""
        return self.consume(key, max_requests, window_seconds)[0]

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        now = time.time()
        with self._lock:
            active = [stamp for stamp in self._buckets.get(key, []) if stamp > now - window_seconds]
            return max(0, max_requests - len(active))


_memory = MemoryRateLimiter()
# Backward-compatible name retained for existing callers and regression tests.
_rate_limiter = _memory
_redis = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=0.15,
    socket_timeout=0.15,
)
_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""
_redis_retry_at = 0.0
_redis_state_lock = Lock()


def consume_limit(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """Atomically consume one request. Redis failure falls back to local protection."""
    redis_key = f"semranko:rate:{key}"
    global _redis_retry_at
    if time.monotonic() < _redis_retry_at:
        return _memory.consume(redis_key, max_requests, window_seconds)
    try:
        count, ttl = _redis.eval(_LUA, 1, redis_key, window_seconds)
        _redis_retry_at = 0.0
        return int(count) <= max_requests, max(1, int(ttl))
    except Exception as exc:  # Redis outage must not remove all abuse protection.
        with _redis_state_lock:
            _redis_retry_at = time.monotonic() + 5.0
        logger.warning("Redis rate limiter unavailable; using local fallback: %s", type(exc).__name__)
        return _memory.consume(redis_key, max_requests, window_seconds)


def clear_limit(key: str) -> None:
    redis_key = f"semranko:rate:{key}"
    try:
        _redis.delete(redis_key)
    except Exception:
        _memory.clear(redis_key)


def client_ip(request: Request) -> str:
    # Do not trust spoofable forwarding headers here; the edge proxy should pass
    # the real peer address to the application server.
    return request.client.host if request.client else "unknown"


def rate_limit(max_requests: int = 10, window_seconds: int = 60, key_func: Optional[Callable] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                request = next((arg for arg in args if isinstance(arg, Request)), None)
            if request is None:
                return func(*args, **kwargs)

            key = key_func(request, kwargs) if key_func else f"{func.__name__}:ip:{client_ip(request)}"
            allowed, retry_after = consume_limit(key, max_requests, window_seconds)
            if not allowed:
                logger.warning("Rate limit exceeded endpoint=%s", func.__name__)
                raise HTTPException(
                    status_code=429,
                    detail={"error": "RATE_LIMITED", "message": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
