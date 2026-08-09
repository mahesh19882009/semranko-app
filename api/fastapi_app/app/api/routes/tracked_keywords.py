import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import db_session, get_current_user, verify_user_access_privileges
from app.schemas.common import ok
from app.services.credit_service import deduct_credits, get_credit_balance
from app.db.models import TrackedKeyword, User, Keyword, Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracked-keywords", tags=["tracked-keywords"])


@router.get("/stale/{project_id}")
async def get_stale_keywords(
    project_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """Get keywords with stale dataStatus for partial refresh."""
    stale_threshold = datetime.utcnow() - timedelta(days=6)
    
    keywords = db.scalars(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.userId == current_user["id"],
        )
    ).all()
    
    stale_keywords = []
    for kw in keywords:
        tracked = db.scalar(
            select(TrackedKeyword).where(
                TrackedKeyword.userId == current_user["id"],
                TrackedKeyword.keyword == kw.keyword,
                TrackedKeyword.isActive == True,
            )
        )
        
        if tracked:
            is_stale = (
                tracked.dataStatus == "stale" or
                (tracked.lastCheckedAt and tracked.lastCheckedAt < stale_threshold)
            )
            
            if is_stale:
                stale_keywords.append({
                    "id": kw.id,
                    "keyword": kw.keyword,
                    "location": kw.location,
                    "device": kw.device,
                    "tracked_id": tracked.id,
                    "data_status": tracked.dataStatus,
                    "last_checked_at": tracked.lastCheckedAt.isoformat() if tracked.lastCheckedAt else None,
                })
    
    return ok("Stale keywords retrieved", {
        "stale_keywords": stale_keywords,
        "count": len(stale_keywords),
    })


@router.post("/refresh-partial/{project_id}")
async def partial_refresh_keywords(
    project_id: str,
    payload: dict = Body(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(db_session),
    user: dict = Depends(verify_user_access_privileges),
):
    """Partially refresh keywords with stale dataStatus."""
    keyword_ids = payload.get("keyword_ids") or []
    
    if not keyword_ids:
        raise HTTPException(status_code=400, detail="keyword_ids is required")
    
    keywords = db.scalars(
        select(Keyword).where(
            Keyword.id.in_(keyword_ids),
            Keyword.projectId == project_id,
            Keyword.userId == current_user["id"],
        )
    ).all()
    
    if not keywords:
        raise HTTPException(status_code=404, detail="No matching keywords found")
    
    updated = []
    for kw in keywords:
        tracked = db.scalar(
            select(TrackedKeyword).where(
                TrackedKeyword.userId == current_user["id"],
                TrackedKeyword.keyword == kw.keyword,
                TrackedKeyword.isActive == True,
            )
        )
        
        if tracked:
            tracked.dataStatus = "refreshing"
            db.add(tracked)
            updated.append({
                "id": kw.id,
                "keyword": kw.keyword,
                "tracked_id": tracked.id,
                "data_status": "refreshing",
            })
    
    db.commit()
    
    return ok("Partial refresh initiated", {
        "updated": updated,
        "count": len(updated),
    })
