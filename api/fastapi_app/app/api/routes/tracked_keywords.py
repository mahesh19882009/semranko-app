import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import db_session, get_current_user, verify_user_access_privileges
from app.schemas.common import ok
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits, get_credit_balance
from app.db.models import TrackedKeyword, User

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
        raise HTTPException(status_code=404, detail="Tracked keyword not found")

    tracked.trackAio = not tracked.trackAio
    db.add(tracked)
    db.commit()
    db.refresh(tracked)

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

    tracked_keywords = db.scalars(
        select(TrackedKeyword).where(
            TrackedKeyword.id.in_(keyword_ids),
            TrackedKeyword.userId == current_user["id"],
            TrackedKeyword.isActive == True,
        )
    ).all()

    if not tracked_keywords:
        raise HTTPException(status_code=404, detail="No matching tracked keywords found")

    updated = []
    for tk in tracked_keywords:
        tk.trackAio = target_aio
        db.add(tk)
        updated.append({
            "id": tk.id,
            "keyword": tk.keyword,
            "track_aio": tk.trackAio,
        })

    db.flush()
    return ok("Bulk AI tracking updated", {"updated": updated, "count": len(updated)})
