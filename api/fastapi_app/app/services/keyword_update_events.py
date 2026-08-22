import json
import logging
from datetime import datetime

from app.queues.redis_client import get_redis

logger = logging.getLogger(__name__)


def keyword_update_channel(user_id: str, project_id: str) -> str:
    return f"semranko:keyword_updates:{user_id}:{project_id}"


def publish_keyword_update(
    *,
    user_id: str,
    project_id: str,
    keyword: str,
    status: str = "success",
    keyword_id: str | None = None,
    location_code: int | None = None,
    device: str | None = None,
) -> None:
    """
    Publish a lightweight UI notification after keyword data
    has already been committed to PostgreSQL.

    This does NOT contain ranking data and does NOT call DataForSEO.
    PostgreSQL remains the source of truth.
    """
    if not user_id or not project_id:
        return

    payload = {
        "event": "keyword_updated",
        "project_id": project_id,
        "keyword": keyword,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if keyword_id:
        payload["keyword_id"] = keyword_id
    if location_code is not None:
        payload["location_code"] = location_code
    if device:
        payload["device"] = device

    try:
        redis = get_redis()
        redis.publish(
            keyword_update_channel(user_id, project_id),
            json.dumps(payload),
        )
    except Exception as exc:
        # Notification failure must NEVER fail keyword processing.
        logger.warning(
            "Failed to publish keyword update event "
            "user=%s project=%s keyword=%s: %s",
            user_id,
            project_id,
            keyword,
            exc,
        )
