from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.agency_dashboard_service import (
    get_agency_dashboard_data,
    get_project_comparison,
    calculate_roi_metrics,
)

router = APIRouter(prefix="/agency-dashboard", tags=["agency-dashboard"])


@router.get("/overview")
async def get_agency_overview(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get agency dashboard overview data
    """
    data = get_agency_dashboard_data(db, current_user["id"])
    return ok("Agency dashboard data retrieved", data)


@router.get("/comparison")
async def get_project_comparison_endpoint(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get project comparison data
    """
    comparison = get_project_comparison(db, current_user["id"])
    return ok("Project comparison retrieved", {"comparison": comparison})


@router.get("/roi")
async def get_roi_metrics_endpoint(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get ROI metrics for agency dashboard
    """
    metrics = calculate_roi_metrics(db, current_user["id"])
    return ok("ROI metrics retrieved", metrics)
