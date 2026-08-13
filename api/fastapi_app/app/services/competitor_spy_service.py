import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.credit_service import check_credits, deduct_credits, refund_credits, reserve_credits, consume_reserved
from app.core.errors import ApiError
from app.core.config import get_settings
from app.services.feature_usage_service import (
    ensure_feature_available,
    reserve_feature_usage,
    finalize_feature_usage,
    release_feature_usage,
)
from app.services.competitor_cache_service import query_cached_competitor, save_cached_competitor
from app.services.dataforseo_client import _build_labs_cache_key, _get_cached_labs, _set_cached_labs
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()


def spy_competitor_keywords(db: Session, user_id: str, domain: str, location_code: int = 2840, limit: int = 100) -> dict:
    usage = ensure_feature_available(db, user_id, "competitor_spy")
    cached = query_cached_competitor(db, domain, str(location_code))
    if cached is not None:
        return {"keywords": cached.get("keywords", []), "cached": True, "credits_charged": 0, "usage": usage}

    labs_key = _build_labs_cache_key("competitors_domain", domain, location_code, "en")
    labs_cached = _get_cached_labs(labs_key)
    if labs_cached is not None:
        return {"keywords": labs_cached.get("keywords", []), "cached": True, "credits_charged": 0, "usage": usage}

    cost = settings.plan_config.credit_costs.get("competitor_spy", 30)
    usage_reference, usage = reserve_feature_usage(
        db, user_id, "competitor_spy", 1,
        reference=f"competitor-spy-usage:{user_id}:{domain}:{location_code}:{datetime.utcnow().timestamp()}",
    )
    reference = f"competitor_spy:{user_id}:{domain}:{location_code}:{datetime.utcnow().timestamp()}"
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
        release_feature_usage(db, usage_reference)
        raise ApiError(402, f"Insufficient credits for competitor spy. Required: {cost}")

    try:
        keywords = DataForSEOClient.get_competitor_keywords(domain, location_code, limit, db=db, user_id=user_id)

        if not keywords:
            logger.warning("Competitor spy: no keywords returned for domain=%s location_code=%s", domain, location_code)
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: no keywords for competitor spy {domain}")
            release_feature_usage(db, usage_reference)
            db.commit()
            return {"keywords": [], "cached": False, "credits_charged": 0, "usage": ensure_feature_available(db, user_id, "competitor_spy")}

        save_cached_competitor(db, domain, str(location_code), keywords)
        _set_cached_labs(labs_key, {"domain": domain, "keywords": keywords}, ttl=604800)

        consume_reserved(
            db,
            user_id,
            reference,
            float(cost),
            action_type="charge",
            description=f"Competitor spy: {domain}",
        )

        usage = finalize_feature_usage(db, usage_reference, 1)
        db.commit()
        return {"keywords": keywords, "cached": False, "credits_charged": 1, "usage": usage}
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        try:
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: competitor spy failed for {domain}")
            db.commit()
        except Exception:
            db.rollback()
        try:
            release_feature_usage(db, usage_reference)
        except Exception:
            db.rollback()
        logger.error(f"Competitor spy failed for {domain}: {exc}")
        raise ApiError(502, f"Competitor spy failed: {exc}") from exc
