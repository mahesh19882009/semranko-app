import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, verify_user_access_privileges
from app.schemas.common import ok
from app.schemas.keywords import KeywordMetricsRequest, KeywordMetricResult, KeywordIdeasRequest, CompetitorSpyRequest
from app.services.dataforseo_client import DataForSEOClient
from app.services.dataforseo_client import LOCATION_MAP
from app.services.credit_service import check_credits, deduct_credits
from app.services.competitor_cache_service import query_cached_competitor, save_cached_competitor
from app.services.keyword_research_cache_service import save_research_cache
from app.core.config import get_settings
from app.services.keyword_research_service import research_keyword
from app.services.competitor_spy_service import spy_competitor_keywords
from app.core.errors import ApiError
from app.core.rate_limiter import rate_limit

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/keyword-metrics", tags=["keyword-metrics"])


@router.post("/lookup")
@rate_limit(max_requests=5, window_seconds=60)
async def lookup_keyword_metrics(
    request: KeywordMetricsRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
    http_request: Request = None,
):
    verify_user_access_privileges(db, current_user)
    
    keywords = [{"keyword": kw.keyword, "location": kw.location, "device": kw.device} for kw in request.keywords]
    if not keywords:
        raise HTTPException(status_code=400, detail="No keywords provided")

    try:
        cost = settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10)
        check_credits(db, current_user['id'], float(len(keywords) * cost))
        result = DataForSEOClient.get_keyword_metrics(db, current_user['id'], keywords)
        consumed = float(result.get("credits_charged", 0) * cost)
        if consumed > 0:
            deduct_credits(db, current_user['id'], consumed, "KEYWORD_LOOKUP", f"Keyword lookup: {len(keywords)} keyword(s)")
        db.commit()
        return ok("Keyword metrics retrieved", {
            "credits_charged": consumed,
            "cached_count": result.get("cached_count", 0),
            "results": result.get("results", []),
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Keyword metrics lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Keyword metrics lookup failed")


@router.get("/ideas")
@rate_limit(max_requests=10, window_seconds=60)
async def get_keyword_ideas(
    request: Request = None,
    seed_keyword: str = Query(..., description="Seed keyword for ideas"),
    location_code: int = Query(2840, description="DataForSEO location code"),
    location: str = Query("India", description="Location display name"),
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    verify_user_access_privileges(db, current_user)
    
    if not seed_keyword.strip():
        raise HTTPException(status_code=400, detail="seed_keyword is required")

    try:
        result = research_keyword(db, current_user['id'], seed_keyword, location_code)
        return ok("Keyword ideas retrieved", result)
    except ApiError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Keyword ideas failed: %s", e)
        raise HTTPException(status_code=500, detail="Keyword ideas lookup failed")


@router.get("/competitor-spy")
@rate_limit(max_requests=5, window_seconds=60)
async def spy_competitor(
    request: Request = None,
    domain: str = Query(..., description="Competitor domain"),
    location_code: int = Query(2840, description="DataForSEO location code"),
    location: str = Query("India", description="Location display name"),
    limit: int = Query(100, description="Max keywords to return"),
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    verify_user_access_privileges(db, current_user)
    
    if not domain.strip():
        raise HTTPException(status_code=400, detail="domain is required")

    try:
        result = spy_competitor_keywords(db, current_user['id'], domain, location_code, limit)
        return ok("Competitor keywords retrieved", result)
    except ApiError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Competitor spy failed: %s", e)
        raise HTTPException(status_code=500, detail="Competitor spy failed")
