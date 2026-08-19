import json
import hashlib
from typing import Optional
from redis import Redis
from app.core.config import get_settings

settings = get_settings()
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD or None,
    decode_responses=True,
)


def _make_key(prefix: str, args: tuple) -> str:
    raw = json.dumps(args, sort_keys=True, default=str)
    digest = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"semranko:cache:{prefix}:{digest}"


def get_cached(prefix: str, args: tuple) -> Optional[dict]:
    key = _make_key(prefix, args)
    value = redis_client.get(key)
    if value is None:
        return None
    return json.loads(value)


def set_cached(prefix: str, args: tuple, value: dict, ttl_seconds: int) -> None:
    key = _make_key(prefix, args)
    redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))


def increment_usage(counter_key: str, ttl_seconds: int = 35 * 24 * 60 * 60) -> int:
    key = f"semranko:usage:{counter_key}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, ttl_seconds)
    return count


def get_usage(counter_key: str) -> int:
    key = f"semranko:usage:{counter_key}"
    value = redis_client.get(key)
    return int(value) if value is not None else 0
