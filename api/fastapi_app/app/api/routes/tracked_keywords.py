import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import db_session, get_current_user, verify_user_access_privileges
from app.schemas.common import ok
from app.services.credit_service import lock_tracked_keyword, unlock_tracked_keyword, get_active_tracked_keywords
from app.services.team_service import get_team_owner_id
from app.services.credit_service import deduct_credits, get_credit_balance
from app.db.models import TrackedKeyword, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracked-keywords", tags=["tracked-keywords"])


@router.post("/lock")
async def lock_keyword(
    keyword: str,
    location: Optional[str] = None,
    device: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
    user: dict = Depends(verify_user_access_privileges),
):
    keyword = keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    result = lock_tracked_keyword(db, current_user['id'], keyword, location, device)
    return ok("Keyword locked for tracking", result)


@router.post("/unlock")
async def unlock_keyword(
    keyword: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keyword = keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    result = unlock_tracked_keyword(db, current_user['id'], keyword)
    return ok("Keyword unlocked", result)


@router.get("/active")
async def list_active_tracked_keywords(
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    keywords = get_active_tracked_keywords(db, current_user['id'])
    return ok("Active tracked keywords", {"keywords": keywords})


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

    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if (user.selectedPlan or "").strip().lower() == "free_trial":
        raise HTTPException(status_code=403, detail="AI tracking requires a paid plan")

    owner_id = get_team_owner_id(db, current_user["id"])

    if not tracked.trackAio:
        owner_id = get_team_owner_id(db, current_user["id"])
        balance = get_credit_balance(db, owner_id)
        if balance < 20:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: 20, Available: {balance}",
            )
        deduct_credits(db, owner_id, 20, "charge", f"AIO tracking activation: {tracked.keyword}")

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

    owner_id = get_team_owner_id(db, current_user["id"])

    if target_aio:
        activating = [tk for tk in tracked_keywords if not tk.trackAio]
        if activating:
            balance = get_credit_balance(db, owner_id)
            cost = len(activating) * 20
            if balance < cost:
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Required: {cost}, Available: {balance}",
                )
            deduct_credits(db, owner_id, cost, "charge", f"AIO tracking bulk activation: {len(activating)} keywords")

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
