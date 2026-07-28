from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.mock_data_service import (
    MockDataGenerator,
    populate_mock_rank_results,
    populate_mock_backlinks,
    get_mock_competitor_comparison,
)

router = APIRouter(prefix="/mock-data", tags=["mock-data"])


@router.post("/rankings/{project_id}")
def generate_mock_rankings(
    project_id: str,
    days: int = Query(30, description="Number of days of historical data to generate"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Generate mock ranking data for a project's keywords.
    This is for development/testing without DataForSEO API.
    """
    from app.db.models import Project
    
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user["userId"])
    )
    if not project:
        return ok("Project not found", None, status_code=404)
    
    count = populate_mock_rank_results(db, project_id, days)
    
    return ok(
        f"Generated {count} mock rank results for {days} days",
        {"project_id": project_id, "days": days, "results_created": count}
    )


@router.post("/backlinks/{project_id}")
def generate_mock_backlinks(
    project_id: str,
    count: int = Query(50, description="Number of backlinks to generate"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Generate mock backlink data for a project.
    This is for development/testing without DataForSEO API.
    """
    from app.db.models import Project
    
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user["userId"])
    )
    if not project:
        return ok("Project not found", None, status_code=404)
    
    count = populate_mock_backlinks(db, project_id, count)
    
    return ok(
        f"Generated {count} mock backlinks",
        {"project_id": project_id, "backlinks_created": count}
    )


@router.get("/competitor-comparison/{project_id}")
def get_competitor_comparison(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """
    Get mock competitor ranking comparison data.
    This is for development/testing without DataForSEO API.
    """
    from app.db.models import Project
    
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user["userId"])
    )
    if not project:
        return ok("Project not found", None, status_code=404)
    
    comparison = get_mock_competitor_comparison(db, project_id)
    
    return ok(
        "Competitor comparison data retrieved",
        {"project_id": project_id, "competitors": comparison}
    )


@router.get("/single-rank")
def get_single_mock_rank(
    keyword: str = Query(..., description="Keyword to check rank for"),
    domain: str = Query(..., description="Domain to check rank for"),
    device: str = Query("desktop", description="Device type"),
    location: str = Query("India", description="Location"),
):
    """
    Get a single mock ranking result for a keyword/domain.
    This is for development/testing without DataForSEO API.
    """
    mock_data = MockDataGenerator.generate_mock_rank(keyword, domain)
    
    return ok(
        "Mock rank data generated",
        mock_data
    )


@router.get("/rank-history")
def get_mock_rank_history(
    keyword: str = Query(..., description="Keyword to get history for"),
    domain: str = Query(..., description="Domain to check rank for"),
    days: int = Query(30, description="Number of days of history"),
):
    """
    Get mock ranking history for a keyword.
    This is for development/testing without DataForSEO API.
    """
    history = MockDataGenerator.generate_mock_rank_history(keyword, domain, days)
    
    return ok(
        f"Generated {len(history)} days of rank history",
        {"keyword": keyword, "domain": domain, "days": days, "history": history}
    )


@router.get("/serp-features")
def get_mock_serp_features(
    keyword: str = Query(..., description="Keyword to check SERP features for"),
    domain: str = Query(..., description="Domain to check"),
):
    """
    Get mock SERP feature data (featured snippets, etc.).
    This is for development/testing without DataForSEO API.
    """
    features = MockDataGenerator.generate_mock_serp_features(keyword, domain)
    
    return ok(
        "Mock SERP features generated",
        features
    )
