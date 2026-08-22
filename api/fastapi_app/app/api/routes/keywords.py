from fastapi import APIRouter, Depends, HTTPException, Body, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re
import asyncio
import json
from redis.asyncio import Redis as AsyncRedis

from app.api.deps import db_session, get_current_user
from app.core.rate_limiter import rate_limit
from app.core.security import enforce_limits
from app.db.models import Keyword, Project, RankResult
from app.services.keyword_table_service import get_enriched_keywords
from app.services.dataforseo_client import DataForSEOClient, LOCATION_MAP
from app.services.credit_service import deduct_credits, refund_credits, reserve_credits, consume_reserved
from app.services.async_tracking_service import submit_user_tracking_job, get_user_processing_jobs
from app.services.keyword_service import delete_keyword, delete_keywords_bulk
from app.services.plan_service import (
    get_user_or_404,
    ensure_keyword_limit,
    activate_keyword as service_activate_keyword,
    deactivate_keyword as service_deactivate_keyword,
    set_keywords_active_state,
)
from app.core.config import get_settings
from app.core.errors import ApiError
from app.services.keyword_update_events import keyword_update_channel
from app.services.location_catalog import location_label, resolve_keyword_location
from app.services.keyword_identity import effective_location_code, normalize_device, normalize_keyword
from app.utils.export import export_csv, export_xlsx

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/keywords", tags=["keywords"])

KEYWORD_READD_COOLDOWN_DAYS = 30


def _resolve_tracking_location(payload: dict) -> tuple[str, int]:
    """Resolve optional hierarchy before entering the existing Tracking API."""

    details = payload.get("location_details")
    if details is None:
        details = payload.get("location_selection")
    if not isinstance(details, dict):
        details = {}

    country = details.get("country") or payload.get("location") or "India"
    state = details.get("state")
    city = details.get("city")
    requested_code = details.get("location_code") or payload.get("location_code") or None
    try:
        resolved = resolve_keyword_location(country, state, city, requested_code)
    except (TypeError, ValueError) as exc:
        raise ApiError(400, str(exc))
    return resolved["label"], resolved["location_code"]


def _keyword_target_matches(keyword: Keyword, project: Project, location_code: int, device: str) -> bool:
    stored_code = keyword.locationCode or effective_location_code(
        location=keyword.location,
        project_location_code=project.locationCode,
        project_location=project.location,
    )
    try:
        stored_device = normalize_device(keyword.device)
    except ValueError:
        stored_device = "desktop"
    return int(stored_code) == int(location_code) and stored_device == device


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


@router.post("/{project_id}/export")
def export_project_keywords(
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """Export project keywords without invoking tracking/provider work."""

    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user["userId"])
    )
    if not project:
        raise ApiError(404, "Project not found")

    export_format = str(payload.get("format") or "csv").strip().lower()
    if export_format not in {"csv", "xlsx"}:
        raise ApiError(400, "format must be csv or xlsx")

    requested_ids = payload.get("keyword_ids")
    if requested_ids is None:
        requested_ids = []
    if not isinstance(requested_ids, list):
        raise ApiError(400, "keyword_ids must be a list")

    query = select(Keyword).where(
        Keyword.projectId == project_id,
        Keyword.userId == user["userId"],
    )
    if requested_ids:
        keywords = db.scalars(query.where(Keyword.id.in_(requested_ids))).all()
        found_ids = {keyword.id for keyword in keywords}
        if found_ids != set(requested_ids):
            raise ApiError(403, "One or more selected keywords are not authorized for this project")
        requested_order = {keyword_id: index for index, keyword_id in enumerate(requested_ids)}
        keywords.sort(key=lambda keyword: requested_order[keyword.id])
    else:
        # Export All is deliberately independent of the rendered/paginated UI.
        keywords = db.scalars(query.order_by(Keyword.createdAt.asc(), Keyword.id.asc())).all()

    project_location = project.location
    if project_location and project_location.startswith("{"):
        try:
            parsed_location = json.loads(project_location)
            if isinstance(parsed_location, dict):
                project_location = ", ".join(
                    part for part in (
                        parsed_location.get("city"),
                        parsed_location.get("state"),
                        parsed_location.get("country"),
                    ) if part
                ) or parsed_location.get("country")
        except (TypeError, ValueError):
            pass

    rows = [
        (
            keyword.keyword,
            location_label(keyword.location, project_location),
            keyword.device or project.device or "desktop",
        )
        for keyword in keywords
    ]
    columns = ("Keyword", "Location", "Device")
    filename = f"project-{project_id}-keywords.{export_format}"
    if export_format == "xlsx":
        return export_xlsx(columns, rows, filename)
    return export_csv(columns, rows, filename)


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
    location, location_code = _resolve_tracking_location(payload)
    try:
        device = normalize_device(payload.get("device"))
    except ValueError as exc:
        raise ApiError(400, str(exc))

    if not keyword_text:
        raise ApiError(400, "Keyword is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing_active = next(
        (
            row for row in db.scalars(
                select(Keyword).where(
                    Keyword.projectId == project_id,
                    Keyword.keyword == normalized_keyword,
                    Keyword.isActive == True,
                )
            ).all()
            if _keyword_target_matches(row, project, location_code, device)
        ),
        None,
    )
    if existing_active:
        raise ApiError(409, "Keyword already exists for this project")

    existing_inactive = next(
        (
            row for row in db.scalars(
                select(Keyword).where(
                    Keyword.projectId == project_id,
                    Keyword.keyword == normalized_keyword,
                    Keyword.isActive == False,
                    Keyword.deletedAt.is_(None),
                )
            ).all()
            if _keyword_target_matches(row, project, location_code, device)
        ),
        None,
    )
    if existing_inactive:
        raise ApiError(409, "Keyword already exists but is inactive. Activate it instead of adding it again.")

    existing_deleted = next(
        (
            row for row in db.scalars(
                select(Keyword).where(
                    Keyword.projectId == project_id,
                    Keyword.keyword == normalized_keyword,
                    Keyword.isActive == False,
                    Keyword.deletedAt.isnot(None),
                ).order_by(Keyword.deletedAt.desc())
            ).all()
            if _keyword_target_matches(row, project, location_code, device)
        ),
        None,
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

    ensure_keyword_limit(
        db,
        user["userId"],
        additional_count=1,
        lock_user=True,
    )

    keyword = Keyword(
        projectId=project_id,
        userId=user["userId"],
        keyword=normalized_keyword,
        location=location,
        device=device,
        locationCode=location_code,
        volume=None,
        kd=None,
        cpc=None,
        competition=None,
        backlinks=None,
        referring_domains=None,
        intent=None,
        position=None,
        ai_badge=None,
    )
    db.add(keyword)
    db.flush()

    def cleanup_untracked_keyword() -> None:
        db.rollback()
        db.execute(delete(Keyword).where(Keyword.id == keyword.id))
        db.commit()

    try:
        logger.info("CREATE_KEYWORD: calling submit_user_tracking_job for keyword=%s", normalized_keyword)
        single_cost = settings.plan_config.credit_costs.get("add_keyword", 20)
        tracking = submit_user_tracking_job(
            db=db,
            user_id=user["userId"],
            project_id=project_id,
            keywords=[{
                "keyword": normalized_keyword,
                "keyword_id": keyword.id,
                "location": location,
                "location_code": location_code,
                "device": device,
                "project_id": project_id,
                "user_id": user["userId"],
            }],
            domain=project.domain,
            action="add_keyword",
            location_code=location_code,
            language_code="en",
            device=device,
            depth=100,
            cost_per_keyword=single_cost,
        )
        if not tracking.get("refresh_job_id") or not tracking.get("accepted", True):
            cleanup_untracked_keyword()
            raise ApiError(502, f"Tracking job was not created for \"{normalized_keyword}\". Keyword was not added.")
        db.refresh(keyword)
        logger.info("CREATE_KEYWORD: tracking job submitted for keyword=%s", normalized_keyword)
    except ApiError:
        if db.scalar(select(Keyword.id).where(Keyword.id == keyword.id)):
            cleanup_untracked_keyword()
        raise
    except Exception as exc:
        cleanup_untracked_keyword()
        logger.warning("Day-one tracking failed for %s: %s", normalized_keyword, exc)
        raise ApiError(502, f"Day-one tracking failed for \"{normalized_keyword}\". Keyword was not added. {exc}")

    response_data = {
        "id": keyword.id,
        "keyword": keyword.keyword,
        "location": keyword.location,
        "locationCode": keyword.locationCode,
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
        "refresh_job_id": tracking.get("refresh_job_id"),
        "completed_keywords": tracking.get("completed_keywords", []),
        "status": "tracking",
    }
    return JSONResponse(status_code=201, content={"success": True, "message": "Keyword added", "data": response_data})


@router.post("/{project_id}/bulk")
@enforce_limits()
@rate_limit(max_requests=5, window_seconds=60, key_func=lambda r, kw: f"bulk_create_keyword:{kw.get('user', {}).get('userId', 'unknown')}")
def bulk_create_keywords(
    request: Request,
    project_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    keywords = payload.get("keywords", [])
    location, location_code = _resolve_tracking_location(payload)
    try:
        device = normalize_device(payload.get("device"))
    except ValueError as exc:
        raise ApiError(400, str(exc))

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
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(normalized_keywords),
        )
    ).all()
    existing_set = set()
    deleted_map = {}

    for row in existing:
        identity = (row.keyword, int(row.locationCode or effective_location_code(
            location=row.location,
            project_location_code=project.locationCode,
            project_location=project.location,
        )), normalize_device(row.device))
        target = (row.keyword, location_code, device)
        if row.isActive or row.deletedAt is None:
            existing_set.add(identity)
        elif row.deletedAt:
            deleted_map[identity] = row.deletedAt

    added = []
    added_targets = []
    skipped = []
    now = datetime.utcnow()

    for kw in normalized_keywords:
        target = (kw, location_code, device)
        if target in existing_set:
            skipped.append({"keyword": kw, "reason": "already_exists"})
            continue

        if target in deleted_map:
            deleted_at = deleted_map[target]
            days_since_deletion = (now - deleted_at).days
            if days_since_deletion < KEYWORD_READD_COOLDOWN_DAYS:
                remaining = KEYWORD_READD_COOLDOWN_DAYS - days_since_deletion
                skipped.append({"keyword": kw, "reason": f"cooldown_active", "remaining_days": remaining})
                continue
            db.execute(delete(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.keyword == kw,
                Keyword.locationCode == location_code,
                Keyword.device == device,
            ))
            db.commit()

        keyword = Keyword(
            projectId=project_id,
            userId=user["userId"],
            keyword=kw,
            location=location,
            device=device,
            locationCode=location_code,
            volume=None,
            kd=None,
            cpc=None,
            competition=None,
            backlinks=None,
            referring_domains=None,
            intent=None,
            position=None,
            ai_badge=None,
        )
        added.append(kw)
        added_targets.append({
            "keyword": kw,
            "_keyword_row": keyword,
            "location": location,
            "location_code": location_code,
            "device": device,
            "project_id": project_id,
            "user_id": user["userId"],
        })
        existing_set.add(target)

    if added_targets:
        ensure_keyword_limit(
            db,
            user["userId"],
            additional_count=len(added_targets),
            lock_user=True,
        )
        db.add_all([
            target["_keyword_row"]
            for target in added_targets
        ])

    db.commit()

    for target in added_targets:
        target["keyword_id"] = target.pop("_keyword_row").id

    processed = 0
    failed_tracking = 0
    tracking_errors = []
    accepted_keywords = []
    completed_keywords = []

    if added:
        bulk_cost = settings.plan_config.credit_costs.get("bulk_add_keyword", 20)
        try:
            tracking = submit_user_tracking_job(
                db=db,
                user_id=user["userId"],
                project_id=project_id,
                keywords=added_targets,
                domain=project.domain,
                action="bulk_add",
                location_code=location_code,
                language_code="en",
                device=device,
                depth=100,
                cost_per_keyword=bulk_cost,
            )
            accepted_keywords = tracking.get("accepted_keywords", added)
            completed_keywords = tracking.get("completed_keywords", [])
            failed_keywords = tracking.get("failed_keywords", [])
            if failed_keywords:
                failed_ids = [
                    target["keyword_id"]
                    for target in added_targets
                    if target["keyword"] in failed_keywords
                ]
                db.execute(
                    delete(Keyword).where(
                        Keyword.id.in_(failed_ids)
                        if failed_ids
                        else False
                    )
                )
                db.commit()
                failed_tracking = len(failed_keywords)
                tracking_errors = [
                    {"keyword": kw, "error": "tracking submission failed"}
                    for kw in failed_keywords
                ]
            processed = len(accepted_keywords)
        except ApiError:
            db.rollback()
            db.execute(
                delete(Keyword).where(
                    Keyword.id.in_([target["keyword_id"] for target in added_targets]),
                )
            )
            db.commit()
            raise
        except Exception as exc:
            failed_tracking = len(added)
            tracking_errors = [{"keyword": kw, "error": str(exc)} for kw in added]
            logger.warning("Bulk day-one tracking failed for %s: %s", added, exc)
            db.rollback()
            db.execute(
                delete(Keyword).where(
                    Keyword.id.in_([target["keyword_id"] for target in added_targets]),
                )
            )
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
            "keywords": accepted_keywords,
            "accepted_targets": [
                {
                    "id": target["keyword_id"],
                    "keyword_id": target["keyword_id"],
                    "keyword": target["keyword"],
                    "location": target["location"],
                    "location_code": target["location_code"],
                    "device": target["device"],
                }
                for target in added_targets
                if target["keyword"] in accepted_keywords
            ],
            "completed_keywords": completed_keywords,
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
    from app.services.keyword_service import get_project_keywords

    keyword_ids = (payload or {}).get("keyword_ids")
    force = (payload or {}).get("force", False)

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user["userId"]))
    if not project:
        raise ApiError(404, "Project not found")

    if keyword_ids:
        requested_keywords = db.scalars(
            select(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.id.in_(keyword_ids),
                Keyword.isActive == True,
            )
        ).all()
    else:
        requested_keywords = db.scalars(
            select(Keyword).where(
                Keyword.projectId == project_id,
                Keyword.isActive == True,
            )
        ).all()

    if not requested_keywords:
        return JSONResponse(status_code=200, content={"success": True, "data": {"updated": 0, "skipped": 0, "failed": 0}})

    keyword_texts = [kw.keyword for kw in requested_keywords]
    keywords_payload = [
        {
            "keyword": kw.keyword,
            "keyword_id": kw.id,
            "location": kw.location,
            "location_code": kw.locationCode or project.locationCode,
            "device": kw.device or "desktop",
            "project_id": project_id,
            "user_id": user["userId"],
        }
        for kw in requested_keywords
    ]

    manual_cost = settings.plan_config.credit_costs.get("manual_refresh_per_keyword", 20)
    tracking = submit_user_tracking_job(
        db=db,
        user_id=user["userId"],
        project_id=project_id,
        keywords=keywords_payload,
        domain=project.domain,
        action="manual_refresh",
        location_code=project.locationCode or LOCATION_MAP.get(project.location or "India", 2840),
        language_code="en",
        device="desktop",
        depth=100,
        cost_per_keyword=manual_cost,
    )

    return JSONResponse(status_code=200, content={
        "success": True,
        "data": {
            "updated": len(keyword_texts),
            "skipped": 0,
            "refresh_job_id": tracking.get("refresh_job_id"),
            "task_ids": tracking.get("task_ids", []),
        },
    })


@router.get("/{project_id}/events")
async def stream_keyword_updates(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    SSE stream for completed keyword updates.

    This endpoint does not call DataForSEO.
    It only notifies the frontend that committed keyword data
    is ready to be fetched from PostgreSQL.
    """
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.userId == user["userId"],
        )
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    channel = keyword_update_channel(user["userId"], project_id)

    async def event_stream():
        redis = AsyncRedis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        pubsub = redis.pubsub()

        try:
            await pubsub.subscribe(channel)

            yield (
                "event: connected\n"
                'data: {"success": true}\n\n'
            )

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )

                if message and message.get("type") == "message":
                    data = message.get("data")

                    yield (
                        "event: keyword_updated\n"
                        f"data: {data}\n\n"
                    )
                else:
                    yield ": keepalive\n\n"

                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            raise

        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass

            try:
                await pubsub.aclose()
            except Exception:
                pass

            try:
                await redis.aclose()
            except Exception:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{project_id}/processing")
def get_project_processing_jobs(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    jobs = get_user_processing_jobs(db, user["userId"], project_id)
    return {"success": True, "data": jobs}


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
