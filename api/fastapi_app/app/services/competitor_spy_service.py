import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_competitor_spy_limit, get_user_plan_limits_by_id
from app.services.cache_service import increment_usage
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def spy_competitor_keywords(db: Session, user_id: str, domain: str, location: str = "India", limit: int = 100) -> list:
    ensure_competitor_spy_limit(db, user_id, credits_needed=1)

    result = DataForSEOClient.get_competitor_keywords_cached(db, user_id, domain, location, limit)
    keywords = result.get("keywords", [])

    if not keywords:
        raise ApiError(502, "DataForSEO competitor keywords failed")

    from datetime import datetime
    month_key = datetime.utcnow().strftime("%Y-%m")
    increment_usage(f"competitor_spy:{user_id}:{month_key}")

    return keywords
