import secrets
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


def generate_session_token() -> str:
    return secrets.token_hex(32)


def _session_key(user_id: str) -> str:
    return f"semranko:session:{user_id}"


def store_session(user_id: str, token: str) -> None:
    ttl = settings.JWT_ACCESS_EXPIRES_IN_DAYS * 86400
    redis_client.setex(_session_key(user_id), ttl, token)


def validate_session(user_id: str, token: str) -> bool:
    key = _session_key(user_id)
    stored = redis_client.get(key)
    return stored == token


def invalidate_session(user_id: str) -> None:
    redis_client.delete(_session_key(user_id))
