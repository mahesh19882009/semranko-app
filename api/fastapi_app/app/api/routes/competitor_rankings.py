from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.competitor_ranking_service import (
    track_competitor_rankings,
    get_competitor_rank_comparison,
    get_keyword_opportunity_analysis,
    get_competitor_rank_history,
)
from app.services.competitor_alert_service import (
    check_competitor_outranking,
    get_competitor_alert_settings,
    update_competitor_alert_settings,
)

router = APIRouter(prefix="/competitor-rankings", tags=["competitor-rankings"])


@router.post("/track/{project_id}")
def track_competitors(
    project_id: str,
    use_mock: bool = Query(True, description="Use mock data instead of DataForSEO API"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Track rankings for all competitors in a project.
    Uses mock data by default for development.
    """
    result = track_competitor_rankings(db, user["userId"], project_id, use_mock)
    return ok("Competitor rankings tracked", result)


@router.get("/comparison/{project_id}")
def get_comparison(
    project_id: str,
    keyword_id: Optional[str] = Query(None, description="Filter by specific keyword"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Get ranking comparison between your domain and competitors.
    """
    comparison = get_competitor_rank_comparison(db, user["userId"], project_id, keyword_id)
    return ok("Competitor comparison data retrieved", {"competitors": comparison})


@router.get("/opportunities/{project_id}")
def get_opportunities(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Get keyword opportunity analysis - keywords where competitors outrank you.
    """
    opportunities = get_keyword_opportunity_analysis(db, user["userId"], project_id)
    return ok("Keyword opportunities retrieved", {"opportunities": opportunities})


@router.get("/history/{project_id}/{competitor_id}")
def get_history(
    project_id: str,
    competitor_id: str,
    days: int = Query(30, description="Number of days of history"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Get historical ranking data for a specific competitor.
    """
    history = get_competitor_rank_history(db, user["userId"], project_id, competitor_id, days)
    return ok("Competitor rank history retrieved", {"history": history})


@router.post("/check-alerts/{project_id}")
def check_alerts(
    project_id: str,
    alert_threshold: int = Query(5, description="Alert if competitor is within N positions"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Check if any competitors are outranking you and create alerts.
    """
    alerts = check_competitor_outranking(db, user["userId"], project_id, alert_threshold)
    return ok(
        f"Competitor alert check completed. {len(alerts)} alerts created.",
        {"alerts_created": len(alerts), "alerts": alerts}
    )


@router.get("/alert-settings")
def get_alert_settings(
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Get user's competitor alert settings.
    """
    settings = get_competitor_alert_settings(db, user["userId"])
    return ok("Alert settings retrieved", settings)


@router.put("/alert-settings")
def update_alert_settings(
    competitorAlerts: Optional[bool] = None,
    dailyKeywordMovement: Optional[bool] = None,
    weeklyAuditSummary: Optional[bool] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Update user's notification settings.
    """
    settings = update_competitor_alert_settings(
        db,
        user["userId"],
        competitorAlerts,
        dailyKeywordMovement,
        weeklyAuditSummary
    )
    return ok("Alert settings updated", settings)
