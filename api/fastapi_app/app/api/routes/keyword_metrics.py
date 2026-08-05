import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, verify_user_access_privileges
from app.schemas.common import ok
from app.schemas.keywords import KeywordMetricsRequest, KeywordMetricResult, KeywordIdeasRequest, CompetitorSpyRequest
from app.services.dataforseo_client import DataForSEOClient
from app.services.credit_service import refund_credits
from app.services.keyword_cache_service import query_cached_keyword, save_cached_keyword
from app.services.competitor_cache_service import query_cached_competitor, save_cached_competitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keyword-metrics", tags=["keyword-metrics"])


@router.post("/lookup")
async def lookup_keyword_metrics(
    request: KeywordMetricsRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    verify_user_access_privileges(db, current_user)
    
    keywords = [{"keyword": kw.keyword, "location": kw.location, "device": kw.device} for kw in request.keywords]
    if not keywords:
        raise HTTPException(status_code=400, detail="No keywords provided")

    try:
        result = DataForSEOClient.get_keyword_metrics(db, current_user['id'], keywords)
        return ok("Keyword metrics retrieved", {
            "credits_charged": result.get("credits_charged", 0),
            "cached_count": result.get("cached_count", 0),
            "results": result.get("results", []),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Keyword metrics lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Keyword metrics lookup failed")


@router.get("/ideas")
async def get_keyword_ideas(
    seed_keyword: str = Query(..., description="Seed keyword for ideas"),
    location: str = Query("India", description="Location"),
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    verify_user_access_privileges(db, current_user)
    
    if not seed_keyword.strip():
        raise HTTPException(status_code=400, detail="seed_keyword is required")

    try:
        result = DataForSEOClient.get_keyword_ideas(db, current_user['id'], seed_keyword, location)
        return ok("Keyword ideas retrieved", result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Keyword ideas failed: %s", e)
        raise HTTPException(status_code=500, detail="Keyword ideas lookup failed")


@router.get("/competitor-spy")
async def spy_competitor(
    domain: str = Query(..., description="Competitor domain"),
    location: str = Query("India", description="Location"),
    limit: int = Query(100, description="Max keywords to return"),
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    verify_user_access_privileges(db, current_user)
    
    if not domain.strip():
        raise HTTPException(status_code=400, detail="domain is required")

    try:
        result = DataForSEOClient.get_competitor_keywords_cached(db, current_user['id'], domain, location, limit)
        return ok("Competitor keywords retrieved", result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Competitor spy failed: %s", e)
        raise HTTPException(status_code=500, detail="Competitor spy failed")
