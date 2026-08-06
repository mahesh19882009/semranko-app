from fastapi import APIRouter, Query, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user, verify_user_access_privileges, verify_user_access_privileges
from app.schemas.common import ok
from app.services.keyword_research_service import research_keyword, add_keywords_to_project
from app.services.competitor_spy_service import spy_competitor_keywords
from app.services.project_onboarding_service import create_project_with_keywords
from app.services.credit_service import check_credits, deduct_credits, refund_credits

router = APIRouter(prefix="/keyword-research", tags=["keyword-research"])


@router.get("/research")
async def research_keyword_endpoint(
    keyword: str = Query(..., description="Keyword to research"),
    location: str = Query("India", description="Location code"),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    verify_user_access_privileges(db, current_user)
    
    # Test mode safeguard
    if x_test_mode == "true":
        # Return mock data without calling external API
        return ok("Keyword research completed (test mode)", {
            "keyword": keyword,
            "location": location,
            "volume": 1000,
            "kd": 50,
            "cpc": 1.5,
            "competition": 0.5,
            "intent": "informational",
            "test_mode": True
        })
    
    try:
        check_credits(db, current_user["userId"], 20)
        result = research_keyword(db, current_user["userId"], keyword, location)
        ideas = result.get("ideas", [])
        if ideas:
            deduct_credits(db, current_user["userId"], 20, "KEYWORD_RESEARCH", f"Keyword research: {keyword}")
        else:
            logger.info("Keyword research returned 0 ideas for '%s', no credits deducted", keyword)
        return ok("Keyword research completed", result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/competitor-spy")
async def competitor_spy_endpoint(
    domain: str = Query(..., description="Competitor domain to spy on"),
    location: str = Query("India", description="Location code"),
    limit: int = Query(100, description="Max keywords to return"),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    verify_user_access_privileges(db, current_user)
    
    # Test mode safeguard
    if x_test_mode == "true":
        # Return mock data without calling external API
        mock_keywords = [
            {
                "keyword": f"keyword_{i}",
                "volume": 1000 + i * 100,
                "kd": 50 + i,
                "position": i + 1,
                "url": f"https://example.com/page{i}"
            }
            for i in range(min(limit, 10))
        ]
        return ok("Competitor keywords retrieved (test mode)", {
            "keywords": mock_keywords,
            "domain": domain,
            "test_mode": True
        })
    
    try:
        check_credits(db, current_user["userId"], 20)
        results = spy_competitor_keywords(db, current_user["userId"], domain, location, limit)
        deduct_credits(db, current_user["userId"], 20, "COMPETITOR_SPY", f"Competitor spy: {domain}")
        return ok("Competitor keywords retrieved", {"keywords": results, "domain": domain})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project/onboard")
async def onboard_project_endpoint(
    name: str = Query(..., description="Project name"),
    domain: str = Query(..., description="Project domain"),
    location: str = Query("India", description="Location code"),
    keywords: list[str] = Query(..., description="Initial keywords"),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode"),
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    verify_user_access_privileges(db, current_user)
    
    # Test mode safeguard
    if x_test_mode == "true":
        # Return mock project ID without creating actual project
        return ok("Project created (test mode)", {
            "projectId": "test-project-id",
            "test_mode": True
        })
    
    try:
        project = create_project_with_keywords(db, current_user["userId"], name, domain, location, keywords)
        return ok("Project created", {"projectId": project.id})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
