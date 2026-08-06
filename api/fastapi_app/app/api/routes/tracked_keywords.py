import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import db_session, get_current_user, verify_user_access_privileges
from app.schemas.common import ok
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits, get_credit_balance
from app.services.aio_service import track_aio_for_project
from app.db.models import TrackedKeyword, User, Keyword, Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracked-keywords", tags=["tracked-keywords"])


@router.post("/toggle-aio/{keyword_id}")
async def toggle_keyword_aio(
    keyword_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
    user: dict = Depends(verify_user_access_privileges),
):
    tracked = db.scalar(
        select(TrackedKeyword).where(
            TrackedKeyword.id == keyword_id,
            TrackedKeyword.userId == current_user["id"],
            TrackedKeyword.isActive == True,
        )
    )

    if not tracked:
        keyword = db.scalar(select(Keyword).where(Keyword.id == keyword_id))
        if not keyword:
            raise HTTPException(status_code=404, detail="Keyword not found")

        tracked = db.scalar(
            select(TrackedKeyword).where(
                TrackedKeyword.userId == current_user["id"],
                TrackedKeyword.keyword == keyword.keyword,
                TrackedKeyword.isActive == True,
            )
        )

        if not tracked:
            now = datetime.utcnow()
            tracked = TrackedKeyword(
                userId=current_user["id"],
                keyword=keyword.keyword,
                location=keyword.location,
                device=keyword.device,
                lockedAt=now,
                lockedUntil=now + timedelta(days=30),
                trackAio=False,
                isActive=True,
            )
            db.add(tracked)
            db.flush()

    tracked.trackAio = not tracked.trackAio
    db.add(tracked)
    db.commit()
    db.refresh(tracked)

    # If AIO tracking was just enabled, fetch initial AIO data for the project
    if tracked.trackAio:
        try:
            kw = db.scalar(select(Keyword).where(Keyword.userId == current_user["id"], Keyword.keyword == tracked.keyword))
            if kw:
                project = db.scalar(select(Project).where(Project.id == kw.projectId))
                if project:
                    track_aio_for_project(db, current_user["id"], project.id)
                    db.commit()
        except Exception as exc:
            logger.error("Failed to fetch initial AIO data after toggle: %s", exc)

    return ok("AI tracking updated", {
        "id": tracked.id,
        "keyword": tracked.keyword,
        "track_aio": tracked.trackAio,
    })


@router.post("/toggle-aio-bulk")
async def bulk_toggle_keyword_aio(
    payload: dict = Body(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
    user: dict = Depends(verify_user_access_privileges),
):
    keyword_ids = payload.get("keyword_ids") or []
    target_aio = bool(payload.get("target_aio"))

    if not keyword_ids:
        raise HTTPException(status_code=400, detail="keyword_ids is required")

    # keyword_ids from frontend are Keyword.id values, not TrackedKeyword.id
    keywords = db.scalars(
        select(Keyword).where(
            Keyword.id.in_(keyword_ids),
            Keyword.userId == current_user["id"],
        )
    ).all()

    if not keywords:
        raise HTTPException(status_code=404, detail="No matching keywords found")

    updated = []
    projects_to_refresh = set()

    for kw in keywords:
        tracked = db.scalar(
            select(TrackedKeyword).where(
                TrackedKeyword.userId == current_user["id"],
                TrackedKeyword.keyword == kw.keyword,
                TrackedKeyword.isActive == True,
            )
        )

        if not tracked:
            now = datetime.utcnow()
            tracked = TrackedKeyword(
                userId=current_user["id"],
                keyword=kw.keyword,
                location=kw.location,
                device=kw.device,
                lockedAt=now,
                lockedUntil=now + timedelta(days=30),
                trackAio=target_aio,
                isActive=True,
            )
            db.add(tracked)
            db.flush()
        else:
            tracked.trackAio = target_aio
            db.add(tracked)

        updated.append({
            "id": tracked.id,
            "keyword": tracked.keyword,
            "track_aio": tracked.trackAio,
        })

        if target_aio and kw.projectId:
            projects_to_refresh.add(kw.projectId)

    db.commit()

    # If enabling AIO, fetch initial data for affected projects
    if target_aio:
        for project_id in projects_to_refresh:
            try:
                track_aio_for_project(db, current_user["id"], project_id)
                db.commit()
            except Exception as exc:
                logger.error("Failed to fetch initial AIO data for project %s: %s", project_id, exc)

    return ok("Bulk AI tracking updated", {"updated": updated, "count": len(updated)})
