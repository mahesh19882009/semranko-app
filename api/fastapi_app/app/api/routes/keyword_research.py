from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.keyword_research_service import (
    research_keyword,
    get_keyword_opportunities,
)

router = APIRouter(prefix="/keyword-research", tags=["keyword-research"])


@router.get("/research")
async def research_keyword_endpoint(
    keyword: str = Query(..., description="Keyword to research"),
    project_id: str = Query(..., description="Project ID"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Research a keyword and get comprehensive data including:
    - Difficulty score
    - Search volume estimate
    - Related keywords
    - Suggestions
    - Opportunity score
    """
    result = await research_keyword(db, keyword, project_id)
    return ok("Keyword research completed", result)


@router.get("/opportunities")
async def get_opportunities_endpoint(
    project_id: str = Query(..., description="Project ID"),
    limit: int = Query(20, description="Number of opportunities to return"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get keyword opportunities for a project
    Returns keywords with high opportunity scores
    """
    opportunities = get_keyword_opportunities(db, project_id, limit)
    return ok("Keyword opportunities retrieved", {"opportunities": opportunities})
