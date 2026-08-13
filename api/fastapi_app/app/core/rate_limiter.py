"""
Simple in-memory rate limiting.

WARNING: This is not distributed-safe. It works only for single-process deployments.
For production multi-instance deployments, replace with Redis-based rate limiting.
"""

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Callable, Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class MemoryRateLimiter:
    """Thread-safe in-memory rate limiter."""

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._buckets[key]
            self._buckets[key] = [t for t in timestamps if t > cutoff]

            if len(self._buckets[key]) >= max_requests:
                return False

            self._buckets[key].append(now)
            return True

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._buckets.get(key, [])
            active = [t for t in timestamps if t > cutoff]
            self._buckets[key] = active
            return max(0, max_requests - len(active))


_rate_limiter = MemoryRateLimiter()


def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60,
    key_func: Optional[Callable] = None,
):
    """Rate limit decorator for FastAPI route handlers.

    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key from request kwargs
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            from fastapi import Request

            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return func(*args, **kwargs)

            if key_func:
                key = key_func(request, kwargs)
            else:
                client_ip = request.client.host if request.client else "unknown"
                key = f"{func.__name__}:{client_ip}"

            if not _rate_limiter.is_allowed(key, max_requests, window_seconds):
                remaining = _rate_limiter.get_remaining(key, max_requests, window_seconds)
                logger.warning(
                    "Rate limit exceeded for key=%s endpoint=%s",
                    key,
                    func.__name__,
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {window_seconds} seconds.",
                    headers={"Retry-After": str(window_seconds)},
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator
