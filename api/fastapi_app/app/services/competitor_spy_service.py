import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_competitor_spy_limit, get_user_plan_limits_by_id
from app.services.cache_service import get_cached, set_cached, increment_usage
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def spy_competitor_keywords(db: Session, user_id: str, domain: str, location: str = "India", limit: int = 100) -> list:
    cached = get_cached("competitor_spy", (domain, location, limit))
    if cached:
        return cached

    ensure_competitor_spy_limit(db, user_id, credits_needed=1)

    results = DataForSEOClient.get_competitor_keywords(domain, location, limit)
    if not results:
        raise ApiError(502, "DataForSEO competitor keywords failed")

    from datetime import datetime
    month_key = datetime.utcnow().strftime("%Y-%m")
    increment_usage(f"competitor_spy:{user_id}:{month_key}")

    set_cached("competitor_spy", (domain, location, limit), results, ttl_seconds=30 * 24 * 60 * 60)
    return results
