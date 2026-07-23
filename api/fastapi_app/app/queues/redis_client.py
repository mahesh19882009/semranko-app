from redis import Redis

from app.core.config import get_settings


def get_redis() -> Redis:
    settings = get_settings()
    if settings.REDIS_URL:
        return Redis.from_url(settings.REDIS_URL)

    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=False,
    )
