import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.cache_service import increment_usage
from app.services.credit_service import check_credits, deduct_credits, refund_credits, reserve_credits, consume_reserved
from app.core.errors import ApiError
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def spy_competitor_keywords(db: Session, user_id: str, domain: str, location_code: int = 2840, limit: int = 100) -> list:
    cost = settings.plan_config.credit_costs.get("competitor_spy", 20)
    reference = f"competitor_spy:{user_id}:{domain}:{location_code}"
    try:
        reserve_credits(
            db,
            user_id,
            float(cost),
            "reservation",
            f"Competitor spy: {domain}",
            reference=reference,
        )
    except Exception as exc:
        raise ApiError(402, f"Insufficient credits for competitor spy. Required: {cost}")

    try:
        result = DataForSEOClient.get_competitor_keywords_cached(db, user_id, domain, location_code, limit)
        keywords = result.get("keywords", [])

        if not keywords:
            logger.warning("Competitor spy: no keywords returned for domain=%s location_code=%s", domain, location_code)
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: no keywords for competitor spy {domain}")
            db.commit()
            return []

        from app.services.competitor_cache_service import save_cached_competitor
        save_cached_competitor(db, domain, str(location_code), keywords)

        from datetime import datetime
        month_key = datetime.utcnow().strftime("%Y-%m")
        increment_usage(f"competitor_spy:{user_id}:{month_key}")

        consume_reserved(
            db,
            user_id,
            reference,
            float(cost),
            action_type="charge",
            description=f"Competitor spy: {domain}",
        )

        db.commit()
        return keywords
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        try:
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: competitor spy failed for {domain}")
            db.commit()
        except Exception:
            db.rollback()
        logger.error(f"Competitor spy failed for {domain}: {exc}")
        raise ApiError(502, f"Competitor spy failed: {exc}") from exc
