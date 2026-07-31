from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.keyword_research_service import research_keyword, add_keywords_to_project
from app.services.competitor_spy_service import spy_competitor_keywords
from app.services.project_onboarding_service import create_project_with_keywords

router = APIRouter(prefix="/keyword-research", tags=["keyword-research"])


@router.get("/research")
async def research_keyword_endpoint(
    keyword: str = Query(..., description="Keyword to research"),
    location: str = Query("India", description="Location code"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        result = research_keyword(db, current_user["userId"], keyword, location)
        return ok("Keyword research completed", result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/competitor-spy")
async def competitor_spy_endpoint(
    domain: str = Query(..., description="Competitor domain to spy on"),
    location: str = Query("India", description="Location code"),
    limit: int = Query(100, description="Max keywords to return"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        results = spy_competitor_keywords(db, current_user["userId"], domain, location, limit)
        return ok("Competitor keywords retrieved", {"keywords": results, "domain": domain})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project/onboard")
async def onboard_project_endpoint(
    name: str = Query(..., description="Project name"),
    domain: str = Query(..., description="Project domain"),
    location: str = Query("India", description="Location code"),
    keywords: list[str] = Query(..., description="Initial keywords"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        project = create_project_with_keywords(db, current_user["userId"], name, domain, location, keywords)
        return ok("Project created", {"projectId": project.id})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
