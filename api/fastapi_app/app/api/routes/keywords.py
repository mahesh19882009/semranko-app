from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.db.models import Keyword, KeywordCache, User, CreditLedger, Project
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits, refund_credits
from app.core.config import get_settings
from app.core.errors import ApiError

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/keywords", tags=["keywords"])


def _get_cached_keyword_data(db: Session, keyword_text: str, location: str):
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword_text,
            KeywordCache.location == location,
        )
    )
    if not cache_entry:
        return None
    return {
        "volume": cache_entry.volume,
        "kd": cache_entry.kd,
        "cpc": cache_entry.cpc,
        "competition": cache_entry.competition,
        "backlinks": cache_entry.backlinks,
        "referring_domains": cache_entry.referring_domains,
        "intent": cache_entry.intent,
        "position": cache_entry.position,
        "ai_badge": cache_entry.ai_badge,
    }


def _update_keyword_from_data(keyword_row: Keyword, data: dict) -> None:
    keyword_row.volume = data.get("volume")
    keyword_row.kd = data.get("kd")
    keyword_row.cpc = data.get("cpc")
    keyword_row.competition = data.get("competition")
    keyword_row.backlinks = data.get("backlinks")
    keyword_row.referring_domains = data.get("referring_domains")
    keyword_row.intent = data.get("intent")
    keyword_row.position = data.get("position")
    keyword_row.ai_badge = data.get("ai_badge")
    keyword_row.updatedAt = datetime.utcnow()


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location: str, domain: str) -> None:
    try:
        cached = _get_cached_keyword_data(db, keyword_text, location)
        if cached:
            keyword_row = db.scalar(
                select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
            )
            if keyword_row:
                _update_keyword_from_data(keyword_row, cached)
                db.commit()
            return

        pingback_url = settings.PINGBACK_URL or f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"
        helper = DataForSeoDashboardHelper()
        helper.fetch_cheapest_dashboard_data(
            [keyword_text],
            domain,
            location_code=2840,
            pingback_url=pingback_url,
            user_id=user_id,
            project_id=None,
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for {keyword_text}: {exc}")
        owner_id = get_team_owner_id(db, user_id)
        refund_credits(db, owner_id, 15, f"Refund: day-one tracking failed for {keyword_text}")


@router.post("/{project_id}")
def create_keyword(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    keyword_text = payload.get("keyword")
    location = payload.get("location") or "India"

    if not keyword_text:
        raise ApiError(400, "Keyword is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
        )
    )
    if existing:
        raise ApiError(409, "Keyword already exists for this project")

    keyword = Keyword(
        projectId=project_id,
        userId=user["userId"],
        keyword=normalized_keyword,
        location=location,
        device=(payload.get("device") or "desktop"),
        volume=0,
        kd=0,
        cpc=0.0,
        competition=0.0,
        backlinks=0.0,
        referring_domains=0.0,
        intent="—",
        position=0,
        ai_badge="—",
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    _apply_day_one_tracking(db, user["userId"], normalized_keyword, location, project.domain)

    db.refresh(keyword)
    return JSONResponse(status_code=201, content={"success": True, "message": "Keyword added", "data": {
        "id": keyword.id,
        "keyword": keyword.keyword,
        "location": keyword.location,
        "device": keyword.device,
        "volume": keyword.volume,
        "kd": keyword.kd,
        "cpc": keyword.cpc,
        "competition": keyword.competition,
        "backlinks": keyword.backlinks,
        "referring_domains": keyword.referring_domains,
        "intent": keyword.intent,
        "position": keyword.position,
        "ai_badge": keyword.ai_badge,
        "isActive": keyword.isActive,
        "createdAt": keyword.createdAt.isoformat() if keyword.createdAt else None,
        "updatedAt": keyword.updatedAt.isoformat() if keyword.updatedAt else None,
    }})


@router.post("/{project_id}/bulk")
def bulk_create_keywords(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keywords = payload.get("keywords", [])
    location = payload.get("location") or "India"

    if not keywords:
        raise ApiError(400, "keywords list is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keywords = []
    for kw in keywords:
        kw = kw.strip().lower()
        if kw:
            normalized_keywords.append(kw)

    if not normalized_keywords:
        return {"success": True, "message": "No valid keywords provided", "data": {"added": 0, "skipped": 0, "keywords": []}}

    existing = db.scalars(
        select(Keyword.keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(normalized_keywords),
        )
    ).all()
    existing_set = set(existing)

    added = []
    for kw in normalized_keywords:
        if kw in existing_set:
            continue

        keyword = Keyword(
            projectId=project_id,
            userId=user["userId"],
            keyword=kw,
            location=location,
            device="desktop",
            volume=0,
            kd=0,
            cpc=0.0,
            competition=0.0,
            backlinks=0.0,
            referring_domains=0.0,
            intent="—",
            position=0,
            ai_badge="—",
        )
        db.add(keyword)
        added.append(kw)
        existing_set.add(kw)

    if added:
        owner_id = get_team_owner_id(db, user["userId"])
        credits_needed = len(added) * 15
        deduct_credits(db, owner_id, float(credits_needed), "ON_DEMAND_ADD", f"Day-one tracking: {len(added)} keyword(s)")

    db.commit()

    for kw_text in added:
        _apply_day_one_tracking(db, user["userId"], kw_text, location, project.domain)

    return {
        "success": True,
        "message": f"Added {len(added)} keywords, skipped {len(normalized_keywords) - len(added)} duplicates",
        "data": {
            "added": len(added),
            "skipped": len(normalized_keywords) - len(added),
            "keywords": added,
        },
    }
