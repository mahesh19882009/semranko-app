from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from typing import Optional
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re

from app.api.deps import db_session, get_current_user
from app.core.rate_limiter import rate_limit
from app.core.security import enforce_limits
from app.db.models import Keyword, Project, RankResult
from app.services.keyword_table_service import get_enriched_keywords
from app.services.dataforseo_client import DataForSEOClient, LOCATION_MAP
from app.services.credit_service import deduct_credits, refund_credits, reserve_credits, consume_reserved
from app.services.keyword_service import delete_keyword, delete_keywords_bulk
from app.services.plan_service import (
    get_user_or_404,
    activate_keyword as service_activate_keyword,
    deactivate_keyword as service_deactivate_keyword,
    set_keywords_active_state,
)
from app.core.config import get_settings
from app.core.errors import ApiError

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/keywords", tags=["keywords"])

KEYWORD_READD_COOLDOWN_DAYS = 30


def _calculate_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0


def _update_keyword_from_data(db: Session, keyword_row: Keyword, data: dict) -> None:
    updates = {}
    for field in ["volume", "kd", "cpc", "competition", "backlinks", "referring_domains", "intent", "position", "ai_badge", "ai_description", "check_url"]:
        value = data.get(field)
        if value is not None:
            if field == "ai_description" and isinstance(value, str):
                value = re.sub(r'\.{3}\s*Read more$', '', value.strip()) or None
            updates[field] = value

    position = data.get("position")
    if position is not None:
        updates["visibility"] = _calculate_visibility(position)

    if updates:
        logger.info("Updating keyword %s with fields: %s", keyword_row.keyword, updates)
        for field, value in updates.items():
            setattr(keyword_row, field, value)
        keyword_row.updatedAt = datetime.utcnow()
    else:
        logger.warning("No fields to update for keyword %s from data keys: %s", keyword_row.keyword, list(data.keys()))


def _is_valid_keyword_data(data: dict) -> bool:
    if not data:
        return False
    data_fields = ["volume", "kd", "cpc", "competition", "backlinks", "referring_domains", "intent", "position", "ai_badge"]
    result = any(data.get(field) is not None for field in data_fields)
    logger.info("_is_valid_keyword_data for %s: %s", data.get("keyword", "unknown"), result)
    return result


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location_code: int, domain: str, cost: int | None = None) -> bool:
    """
    Fetch DataForSEO data and update Keyword.
    Reserves credits before the API call and consumes them on success.
    Returns True if data was fetched from API, False if no data fetched.
    Raises on failure so callers can return an error response.
    """
    logger.info("DAY_ONE_TRACKING START: keyword=%s location=%s domain=%s", keyword_text, location_code, domain)
    try:
        from app.db.models import TrackedKeyword
        aio_keyword_texts = set(
            row.keyword
            for row in db.scalars(
                select(TrackedKeyword).where(
                    TrackedKeyword.userId == user_id,
                    TrackedKeyword.isActive == True,
                    TrackedKeyword.trackAio == True,
                    TrackedKeyword.keyword == keyword_text,
                )
            ).all()
        )

        if cost is None:
            cost = settings.plan_config.credit_costs.get("add_keyword", 20)
        reference = f"dayone:{user_id}:{keyword_text}:{datetime.utcnow().timestamp()}"
        try:
            reserve_credits(
                db,
                user_id,
                float(cost),
                "reservation",
                f"Day-one tracking reservation: {keyword_text}",
                reference=reference,
            )
        except Exception as exc:
            logger.error(f"Day-one tracking credit reservation failed: {exc}")
            raise ApiError(402, f"Insufficient credits for day-one tracking. Required: {cost}")

        from app.services.dataforseo_client import check_dfs_cost_ceiling
        try:
            check_dfs_cost_ceiling(db, user_id, 0.037)
        except Exception as exc:
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: DFS cost ceiling exceeded for {keyword_text}")
            db.commit()
            raise ApiError(403, str(exc.detail) if hasattr(exc, "detail") else str(exc))

        rows = DataForSEOClient.fetch_dashboard_data(
            [keyword_text],
            domain,
            location_code=location_code,
            language_code="en",
            aio_keyword_texts=aio_keyword_texts,
        )

        if not rows:
            logger.warning("Day-one tracking: no rows returned from DataForSEO for %s", keyword_text)
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: no DataForSEO data for {keyword_text}")
            db.commit()
            return False

        row = rows[0]
        logger.info("Day-one tracking raw data for %s: %s", keyword_text, row)
        logger.info("Day-one tracking ai_description for %s: %s", keyword_text, row.get("ai_description"))

        if not _is_valid_keyword_data(row):
            logger.warning("Day-one tracking: all null data returned from DataForSEO for %s. Full row=%s", keyword_text, row)
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: empty DataForSEO data for {keyword_text}")
            db.commit()
            return False

        consume_reserved(
            db,
            user_id,
            reference,
            float(cost),
            action_type="charge",
            description=f"Day-one tracking: {keyword_text}",
        )

        try:
            keyword_row = db.scalar(
                select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
            )
            if keyword_row:
                _update_keyword_from_data(db, keyword_row, row)
            db.commit()
        except Exception as exc:
            db.rollback()
            try:
                refund_reserved(db, user_id, reference, float(cost), description=f"Refund: day-one tracking DB update failed for {keyword_text}")
                db.commit()
            except Exception:
                db.rollback()
            raise

        return True
    except ApiError:
        raise
    except Exception:
        db.rollback()
        raise


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


@router.delete("/bulk")
def bulk_remove_keywords(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword_ids = payload.get("keyword_ids", [])
    deleted = delete_keywords_bulk(db, user["userId"], keyword_ids)
    return {"success": True, "message": f"Deleted {deleted} keywords"}


@router.post("/bulk/status")
def bulk_set_keyword_status(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword_ids = payload.get("keyword_ids", [])
    active = payload.get("active")
    if not isinstance(active, bool):
        raise ApiError(400, "active must be true or false")
    result = set_keywords_active_state(db, user["userId"], keyword_ids, active)
    action = "activated" if active else "deactivated"
    return {
        "success": True,
        "message": f"{result['updatedCount']} keyword(s) {action}",
        "data": result,
    }


@router.delete("/{keyword_id}")
@rate_limit(max_requests=20, window_seconds=60)
def remove_keyword(
    request: Request,
    keyword_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    delete_keyword(db, user["userId"], keyword_id)
    return {"success": True, "message": "Keyword deleted successfully"}


@router.post("/{project_id}")
@enforce_limits(resource_type='keyword')
@rate_limit(max_requests=20, window_seconds=60, key_func=lambda r, kw: f"create_keyword:{kw.get('user', {}).get('userId', 'unknown')}")
def create_keyword(
    request: Request,
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> JSONResponse:
    keyword_text = payload.get("keyword")
    location = payload.get("location") or "India"
    location_code = payload.get("location_code") or LOCATION_MAP.get(location, 2840)

    if not keyword_text:
        raise ApiError(400, "Keyword is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing_active = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
            Keyword.isActive == True,
        )
    )
    if existing_active:
        raise ApiError(409, "Keyword already exists for this project")

    existing_inactive = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
            Keyword.isActive == False,
            Keyword.deletedAt.is_(None),
        )
    )
    if existing_inactive:
        raise ApiError(409, "Keyword already exists but is inactive. Activate it instead of adding it again.")

    existing_deleted = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
            Keyword.isActive == False,
            Keyword.deletedAt.isnot(None),
        ).order_by(Keyword.deletedAt.desc())
    )
    if existing_deleted:
        cooldown_days = 30
        deleted_at = existing_deleted.deletedAt
        if deleted_at:
            days_since_deletion = (datetime.utcnow() - deleted_at).days
            if days_since_deletion < cooldown_days:
                remaining = cooldown_days - days_since_deletion
                raise ApiError(
                    403,
                    f"Keyword was recently deleted. You can re-add it in {remaining} day(s).",
                )
        db.execute(delete(Keyword).where(Keyword.id == existing_deleted.id))
        db.commit()

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
    db.flush()

    try:
        logger.info("CREATE_KEYWORD: calling _apply_day_one_tracking for keyword=%s", normalized_keyword)
        single_cost = settings.plan_config.credit_costs.get("add_keyword", 20)
        tracked = _apply_day_one_tracking(db, user["userId"], normalized_keyword, location_code, project.domain, cost=single_cost)
        if not tracked:
            db.rollback()
            raise ApiError(502, f"Day-one tracking returned no data for \"{normalized_keyword}\". Keyword was not added.")
        db.refresh(keyword)
        logger.info("CREATE_KEYWORD: day-one tracking completed for keyword=%s", normalized_keyword)
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        logger.warning("Day-one tracking failed for %s: %s", normalized_keyword, exc)
        raise ApiError(502, f"Day-one tracking failed for \"{normalized_keyword}\". Keyword was not added. {exc}")

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
    return JSONResponse(status_code=201, content={"success": True, "message": "Keyword added", "data": response_data})


@router.post("/{project_id}/bulk")
@enforce_limits(resource_type='keyword')
@rate_limit(max_requests=5, window_seconds=60, key_func=lambda r, kw: f"bulk_create_keyword:{kw.get('user', {}).get('userId', 'unknown')}")
def bulk_create_keywords(
    request: Request,
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keywords = payload.get("keywords", [])
    location = payload.get("location") or "India"
    location_code = payload.get("location_code") or LOCATION_MAP.get(location, 2840)
    device = payload.get("device") or "desktop"

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
        select(Keyword.keyword, Keyword.isActive, Keyword.deletedAt).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(normalized_keywords),
        )
    ).all()
    existing_set = set()
    deleted_map = {}

    for kw, is_active, deleted_at in existing:
        if is_active or deleted_at is None:
            existing_set.add(kw)
        elif deleted_at:
            deleted_map[kw] = deleted_at

    added = []
    skipped = []
    now = datetime.utcnow()

    for kw in normalized_keywords:
        if kw in existing_set:
            skipped.append({"keyword": kw, "reason": "already_exists"})
            continue

        if kw in deleted_map:
            deleted_at = deleted_map[kw]
            days_since_deletion = (now - deleted_at).days
            if days_since_deletion < KEYWORD_READD_COOLDOWN_DAYS:
                remaining = KEYWORD_READD_COOLDOWN_DAYS - days_since_deletion
                skipped.append({"keyword": kw, "reason": f"cooldown_active", "remaining_days": remaining})
                continue
            db.execute(delete(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw))
            db.commit()

        keyword = Keyword(
            projectId=project_id,
            userId=user["userId"],
            keyword=kw,
            location=location,
            device=device,
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
            bulk_cost = settings.plan_config.credit_costs.get("bulk_add_keyword", 20)
            tracked = _apply_day_one_tracking(db, user["userId"], kw_text, location_code, project.domain, cost=bulk_cost)
            if not tracked:
                failed_keyword = db.scalar(
                    select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text)
                )
                if failed_keyword:
                    db.delete(failed_keyword)
                    db.commit()
                failed_tracking += 1
                tracking_errors.append({"keyword": kw_text, "error": "No data returned from DataForSEO"})
                logger.warning("Day-one tracking returned no data for %s", kw_text)
                continue
            processed += 1
        except ApiError:
            raise
        except Exception as exc:
            failed_tracking += 1
            tracking_errors.append({"keyword": kw_text, "error": str(exc)})
            logger.warning("Day-one tracking failed for %s: %s", kw_text, exc)
            failed_keyword = db.scalar(
                select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text)
            )
            if failed_keyword:
                db.delete(failed_keyword)
                db.commit()

    message = f"Added {processed} keywords"
    if skipped_count := len(normalized_keywords) - len(added):
        message += f", skipped {skipped_count} duplicates/cooldown"
    if failed_tracking:
        message += f", {failed_tracking} tracking failures"

    return {
        "success": True,
        "message": message,
        "data": {
            "added": processed,
            "skipped": len(normalized_keywords) - len(added),
            "skipped_details": skipped,
            "keywords": added[:processed],
            "processed": processed,
            "failed_tracking": failed_tracking,
            "tracking_errors": tracking_errors,
        },
    }


@router.post("/{project_id}/refresh")
@rate_limit(max_requests=10, window_seconds=60)
def refresh_project_keywords(
    project_id: str,
    request: Request = None,
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


@router.post("/{keyword_id}/activate")
def activate_keyword(
    keyword_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword = service_activate_keyword(db, user["userId"], keyword_id)
    return {"success": True, "data": {"id": keyword.id, "isActive": keyword.isActive}}


@router.post("/{keyword_id}/deactivate")
def deactivate_keyword(
    keyword_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword = service_deactivate_keyword(db, user["userId"], keyword_id)
    return {"success": True, "data": {"id": keyword.id, "isActive": keyword.isActive}}


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
    for i, key in enumerate(sorted(weekly_data.keys())):
        wd = weekly_data[key]
        avg_pos = sum(wd["positions"]) / len(wd["positions"]) if wd["positions"] else 0
        avg_vis = sum(wd["visibilities"]) / len(wd["visibilities"]) if wd["visibilities"] else keyword_visibility
        traffic = sum(wd["etvs"]) if wd["etvs"] else 0

        position_change = None
        if i > 0:
            prev_pos = history[-1].get("avg_position")
            if prev_pos is not None and avg_pos is not None:
                pos_diff = round(avg_pos - prev_pos, 1)
                position_change = {
                    "previous": prev_pos,
                    "current": avg_pos,
                    "difference": pos_diff,
                    "direction": "up" if pos_diff < 0 else ("down" if pos_diff > 0 else "same"),
                    "isPositive": pos_diff < 0,
                }

        history.append({
            "week_start": wd["week_start"],
            "week_end": wd["week_end"],
            "avg_position": round(avg_pos, 1),
            "avg_visibility": round(avg_vis, 2),
            "traffic": round(traffic, 2),
            "positionChange": position_change,
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

    rank_results = db.scalars(
        select(RankResult).where(
            RankResult.projectId == project_id,
            RankResult.checkedAt >= last_week_start,
            RankResult.checkedAt <= this_week_end,
        )
    ).all()

    results_by_keyword = {}
    for row in rank_results:
        kid = row.keywordId
        if kid not in results_by_keyword:
            results_by_keyword[kid] = {"this_week": [], "last_week": []}
        if this_week_start <= row.checkedAt <= this_week_end:
            results_by_keyword[kid]["this_week"].append(row)
        elif last_week_start <= row.checkedAt <= last_week_end:
            results_by_keyword[kid]["last_week"].append(row)

    this_week_positions = []
    this_week_visibilities = []
    this_week_traffic = []
    last_week_positions = []
    last_week_visibilities = []
    last_week_traffic = []

    for kw in keywords:
        kw_results = results_by_keyword.get(kw.id, {"this_week": [], "last_week": []})
        
        for row in kw_results["this_week"]:
            if row.position:
                this_week_positions.append(row.position)
            this_week_traffic.append(row.etv or 0)

        for row in kw_results["last_week"]:
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
