from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.competitor_rank_service import track_competitor_rankings, get_competitor_comparison

router = APIRouter(prefix="/competitor-rankings", tags=["competitor-rankings"])


@router.post("/{project_id}/track")
async def track_competitors(
    project_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = track_competitor_rankings(db, current_user["userId"], project_id, depth=100)
        return ok("Competitor tracking completed", result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/comparison")
async def competitor_comparison(
    project_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        results = get_competitor_comparison(db, current_user["userId"], project_id)
        return ok("Competitor comparison retrieved", {"comparison": results})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
