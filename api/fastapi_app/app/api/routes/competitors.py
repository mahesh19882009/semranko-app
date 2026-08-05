from fastapi import APIRouter, Body, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.competitor_service import (
    create_competitor,
    delete_competitor,
    get_competitors_by_project,
    update_competitor,
)
from app.core.security import enforce_limits

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("/project/{project_id}")
def list_by_project(
    project_id: str, 
    user: dict = Depends(get_current_user), 
    db: Session = Depends(db_session),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode")
) -> dict:
    # Test mode safeguard
    if x_test_mode == "true":
        return ok("Competitors fetched (test mode)", {
            "competitors": [],
            "test_mode": True
        })
    
    competitors = get_competitors_by_project(db, user["userId"], project_id)
    return ok("Competitors fetched", competitors)


@router.post("")
@enforce_limits(resource_type='competitor')
def create(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode")
) -> JSONResponse:
    # Test mode safeguard
    if x_test_mode == "true":
        return JSONResponse(status_code=201, content=ok("Competitor created (test mode)", {
            "id": "test-competitor-id",
            "domain": payload.get("domain", "test.com"),
            "test_mode": True
        }))
    
    project_id = payload.get("projectId")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    competitor = create_competitor(db, user["userId"], payload)
    return JSONResponse(status_code=201, content=ok("Competitor created", competitor))


@router.put("/{competitor_id}")
def update(
    competitor_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode")
) -> dict:
    # Test mode safeguard
    if x_test_mode == "true":
        return ok("Competitor updated (test mode)", {
            "id": competitor_id,
            "test_mode": True
        })
    
    competitor = update_competitor(db, user["userId"], competitor_id, payload)
    return ok("Competitor updated", competitor)


@router.delete("/{competitor_id}")
def remove_competitor(
    competitor_id: str, 
    user: dict = Depends(get_current_user), 
    db: Session = Depends(db_session),
    x_test_mode: Optional[str] = Header(None, alias="X-Test-Mode")
) -> dict:
    # Test mode safeguard
    if x_test_mode == "true":
        return ok("Competitor deleted (test mode)", {"test_mode": True})
    
    delete_competitor(db, user["userId"], competitor_id)
    return ok("Competitor deleted", None)
