from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api.deps import db_session, get_current_user
from app.db.models import Keyword, KeywordCache, Project, RankResult
from app.services.keyword_table_service import get_enriched_keywords
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits
from app.services.keyword_service import delete_keyword, delete_keywords_bulk
from app.core.config import get_settings
from app.core.errors import ApiError

import logging
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


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location: str, domain: str) -> bool:
    """
    Fetch DataForSEO data and update Keyword + KeywordCache.
    Charges user-configured credits only after a successful API response.
    Returns True if data was fetched from API, False if served from cache.
    Raises on failure so callers can return an error response.
    """
    try:
        cached = _get_cached_keyword_data(db, keyword_text, location)
        if cached:
            keyword_row = db.scalar(
                select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
            )
            if keyword_row:
                _update_keyword_from_data(keyword_row, cached)
                _update_or_create_cache_from_route(db, keyword_text, location, cached)
                db.commit()
            # Always charge 20 credits for adding a keyword, even if using cached data
            owner_id = get_team_owner_id(db, user_id)
            deduct_credits(db, owner_id, 20, "KEYWORD_ADD", f"Keyword add: {keyword_text} (cached data)")
            return False

        helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
        rows = helper.fetch_cheapest_dashboard_data(
            [keyword_text],
            domain,
            location_code=2840,
            language_code="en",
        )

        if not rows:
            logger.warning("Day-one tracking: no data returned from DataForSEO for %s", keyword_text)
            return False

        row = rows[0]
        owner_id = get_team_owner_id(db, user_id)
        deduct_credits(db, owner_id, 20, "ON_DEMAND_ADD", f"Day-one tracking: {keyword_text}")

        keyword_row = db.scalar(
            select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
        )
        if keyword_row:
            _update_keyword_from_data(keyword_row, row)
        _update_or_create_cache_from_route(db, keyword_text, location, row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def _update_or_create_cache_from_route(db: Session, keyword_text: str, location: str, data: dict) -> None:
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword_text,
            KeywordCache.location == location,
        )
    )
    if cache_entry:
        cache_entry.volume = data.get("volume")
        cache_entry.kd = data.get("kd")
        cache_entry.cpc = data.get("cpc")
        cache_entry.competition = data.get("competition")
        cache_entry.backlinks = data.get("backlinks")
        cache_entry.referring_domains = data.get("referring_domains")
        cache_entry.intent = data.get("intent")
        cache_entry.position = data.get("position")
        cache_entry.ai_badge = data.get("ai_badge")
        cache_entry.lastApiCallAt = datetime.utcnow()
        cache_entry.updatedAt = datetime.utcnow()
    else:
        cache_entry = KeywordCache(
            keyword=keyword_text,
            location=location,
            volume=data.get("volume"),
            kd=data.get("kd"),
            cpc=data.get("cpc"),
            competition=data.get("competition"),
            backlinks=data.get("backlinks"),
            referring_domains=data.get("referring_domains"),
            intent=data.get("intent"),
            position=data.get("position"),
            ai_badge=data.get("ai_badge"),
            lastApiCallAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
        )
        db.add(cache_entry)


@router.get("/{project_id}/table")
def get_keyword_table(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keywords = get_enriched_keywords(db, user["userId"], project_id)
    return {"success": True, "data": {"rows": keywords}}


@router.get("/{project_id}")
def list_keywords(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.services.keyword_service import get_project_keywords
    keywords = get_project_keywords(db, user["userId"], project_id)
    return {"success": True, "data": keywords}


@router.delete("/{keyword_id}")
def remove_keyword(
    keyword_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    delete_keyword(db, user["userId"], keyword_id)
    return {"success": True, "message": "Keyword deleted successfully"}


@router.delete("/bulk")
def bulk_remove_keywords(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword_ids = payload.get("keyword_ids", [])
    deleted = delete_keywords_bulk(db, user["userId"], keyword_ids)
    return {"success": True, "message": f"Deleted {deleted} keywords"}


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

    tracking_error = None
    try:
        _apply_day_one_tracking(db, user["userId"], normalized_keyword, location, project.domain)
        db.refresh(keyword)
    except Exception as exc:
        db.rollback()
        tracking_error = str(exc)
        logger.warning("Day-one tracking failed for %s: %s", normalized_keyword, exc)

    response_data = {
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
    }
    if tracking_error:
        return JSONResponse(status_code=201, content={
            "success": True,
            "message": "Keyword added but data tracking failed",
            "warning": tracking_error,
            "data": response_data,
        })
    return JSONResponse(status_code=201, content={"success": True, "message": "Keyword added", "data": response_data})


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

    db.commit()

    processed = 0
    failed_tracking = 0
    tracking_errors = []
    for kw_text in added:
        try:
            tracked = _apply_day_one_tracking(db, user["userId"], kw_text, location, project.domain)
            if tracked:
                processed += 1
        except Exception as exc:
            failed_tracking += 1
            tracking_errors.append({"keyword": kw_text, "error": str(exc)})
            logger.warning("Day-one tracking failed for %s: %s", kw_text, exc)

    return {
        "success": True,
        "message": f"Added {len(added)} keywords, skipped {len(normalized_keywords) - len(added)} duplicates" + (f", {failed_tracking} tracking failures" if failed_tracking else ""),
        "data": {
            "added": len(added),
            "skipped": len(normalized_keywords) - len(added),
            "keywords": added,
            "processed": processed,
            "failed_tracking": failed_tracking,
            "tracking_errors": tracking_errors,
        },
    }


@router.post("/{project_id}/refresh")
def refresh_project_keywords(
    project_id: str,
    payload: Optional[dict] = Body(default=None),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    from app.services.keyword_update_service import refresh_keyword_data

    keyword_ids = (payload or {}).get("keyword_ids")
    force = (payload or {}).get("force", False)
    result = refresh_keyword_data(db, user["userId"], project_id, keyword_ids, force=force)
    if not result.get("success"):
        status = 402 if result.get("error") == "INSUFFICIENT_CREDITS" else 400
        return JSONResponse(status_code=status, content=result)
    return JSONResponse(status_code=200, content={"success": True, "data": result})


def _get_week_bounds(dt: datetime):
    monday = dt - timedelta(days=dt.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


@router.get("/{project_id}/history/{keyword_id}")
def get_keyword_history(
    project_id: str,
    keyword_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword = db.scalar(
        select(Keyword).where(Keyword.id == keyword_id, Keyword.projectId == project_id, Keyword.userId == user["userId"])
    )
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    results = db.scalars(
        select(RankResult)
        .where(
            RankResult.projectId == project_id,
            RankResult.keywordId == keyword_id,
        )
        .order_by(RankResult.checkedAt.asc())
    ).all()

    weekly_data = {}
    for row in results:
        week_start, week_end = _get_week_bounds(row.checkedAt)
        key = week_start.isoformat()
        if key not in weekly_data:
            weekly_data[key] = {
                "week_start": key,
                "week_end": week_end.isoformat(),
                "positions": [],
                "visibilities": [],
                "etvs": [],
            }
        weekly_data[key]["positions"].append(row.position or 0)
        weekly_data[key]["visibilities"].append(0.0)
        weekly_data[key]["etvs"].append(row.etv or 0)

    keyword_visibility = db.scalar(
        select(Keyword.visibility).where(Keyword.id == keyword_id)
    ) or 0.0

    history = []
    for key in sorted(weekly_data.keys()):
        wd = weekly_data[key]
        avg_pos = sum(wd["positions"]) / len(wd["positions"]) if wd["positions"] else 0
        avg_vis = sum(wd["visibilities"]) / len(wd["visibilities"]) if wd["visibilities"] else keyword_visibility
        traffic = sum(wd["etvs"]) if wd["etvs"] else 0
        history.append({
            "week_start": wd["week_start"],
            "week_end": wd["week_end"],
            "avg_position": round(avg_pos, 1),
            "avg_visibility": round(avg_vis, 2),
            "traffic": round(traffic, 2),
        })

    return {
        "success": True,
        "data": {
            "keyword": keyword.keyword,
            "history": history[-8:],
        },
    }


@router.get("/{project_id}/weekly-comparison")
def get_weekly_comparison(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    now = datetime.utcnow()
    this_week_start, this_week_end = _get_week_bounds(now)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(seconds=1)

    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id, Keyword.userId == user["userId"])
    ).all()

    this_week_positions = []
    this_week_visibilities = []
    this_week_traffic = []
    last_week_positions = []
    last_week_visibilities = []
    last_week_traffic = []

    for kw in keywords:
        this_results = db.scalars(
            select(RankResult).where(
                RankResult.projectId == project_id,
                RankResult.keywordId == kw.id,
                RankResult.checkedAt >= this_week_start,
                RankResult.checkedAt <= this_week_end,
            )
        ).all()
        for row in this_results:
            if row.position:
                this_week_positions.append(row.position)
            this_week_traffic.append(row.etv or 0)

        last_results = db.scalars(
            select(RankResult).where(
                RankResult.projectId == project_id,
                RankResult.keywordId == kw.id,
                RankResult.checkedAt >= last_week_start,
                RankResult.checkedAt <= last_week_end,
            )
        ).all()
        for row in last_results:
            if row.position:
                last_week_positions.append(row.position)
            last_week_traffic.append(row.etv or 0)

        if kw.visibility is not None:
            this_week_visibilities.append(kw.visibility)
            last_week_visibilities.append(kw.visibility)

    def avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else 0

    def total(lst):
        return round(sum(lst), 2) if lst else 0

    this_avg_pos = avg(this_week_positions) if this_week_positions else 0
    last_avg_pos = avg(last_week_positions) if last_week_positions else 0
    pos_change = round(last_avg_pos - this_avg_pos, 1) if (this_avg_pos or last_avg_pos) else 0
    pos_direction = "up" if pos_change > 0 else ("down" if pos_change < 0 else "same")

    this_avg_vis = avg(this_week_visibilities) if this_week_visibilities else 0
    last_avg_vis = avg(last_week_visibilities) if last_week_visibilities else 0
    vis_change = round(this_avg_vis - last_avg_vis, 2)
    vis_direction = "up" if vis_change > 0 else ("down" if vis_change < 0 else "same")

    this_total_traffic = total(this_week_traffic)
    last_total_traffic = total(last_week_traffic)
    traffic_change = round(this_total_traffic - last_total_traffic, 2)
    traffic_direction = "up" if traffic_change > 0 else ("down" if traffic_change < 0 else "same")

    return {
        "success": True,
        "data": {
            "position": {
                "this_week": this_avg_pos or None,
                "last_week": last_avg_pos or None,
                "change": pos_change or None,
                "direction": pos_direction,
            },
            "visibility": {
                "this_week": this_avg_vis or None,
                "last_week": last_avg_vis or None,
                "change": vis_change or None,
                "direction": vis_direction,
            },
            "traffic": {
                "this_week": this_total_traffic or None,
                "last_week": last_total_traffic or None,
                "change": traffic_change or None,
                "direction": traffic_direction,
            },
        },
    }
