from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.db.models import User
from app.schemas.common import ok
from app.services.lhf_service import (
    get_low_hanging_fruits,
    get_lhf_summary,
)

router = APIRouter(prefix="/lhf", tags=["low-hanging-fruits"])


@router.get("/opportunities")
async def get_lhf_opportunities(
    project_id: str = Query(..., description="Project ID"),
    limit: int = Query(20, description="Number of opportunities to return"),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get low hanging fruit opportunities for a project
    Returns keywords with high potential for quick ranking improvements
    """
    opportunities = get_low_hanging_fruits(db, project_id, limit)
    return ok("Low hanging fruit opportunities retrieved", {"opportunities": opportunities})


@router.get("/summary")
async def get_lhf_summary_endpoint(
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics for low hanging fruits
    Includes total opportunities, quick wins, and average score
    """
    summary = get_lhf_summary(db, project_id)
    return ok("LHF summary retrieved", summary)
