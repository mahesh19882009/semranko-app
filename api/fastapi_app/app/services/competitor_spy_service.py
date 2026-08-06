import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.cache_service import increment_usage
from app.services.credit_service import check_credits, deduct_credits, refund_credits
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def spy_competitor_keywords(db: Session, user_id: str, domain: str, location: str = "India", limit: int = 100) -> list:
    try:
        result = DataForSEOClient.get_competitor_keywords_cached(db, user_id, domain, location, limit)
        keywords = result.get("keywords", [])

        if not keywords:
            logger.warning("Competitor spy: no keywords returned for domain=%s location=%s", domain, location)
            raise ApiError(502, "Competitor keywords lookup returned no results. The domain may not have enough SERP data for this location.")

        from datetime import datetime
        month_key = datetime.utcnow().strftime("%Y-%m")
        increment_usage(f"competitor_spy:{user_id}:{month_key}")

        return keywords
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"Competitor spy failed for {domain}: {exc}")
        raise ApiError(502, f"Competitor spy failed: {exc}") from exc
