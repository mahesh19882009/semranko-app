from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.competitor_service import (
    create_competitor,
    delete_competitor,
    get_competitors_by_project,
    update_competitor,
)

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("/project/{project_id}")
def list_by_project(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    competitors = get_competitors_by_project(db, user["userId"], project_id)
    return ok("Competitors fetched", competitors)


@router.post("")
def create(payload: dict = Body(...), user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> JSONResponse:
    competitor = create_competitor(db, user["userId"], payload)
    return JSONResponse(status_code=201, content=ok("Competitor created", competitor))


@router.put("/{competitor_id}")
def update(
    competitor_id: str,
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    competitor = update_competitor(db, user["userId"], competitor_id, payload)
    return ok("Competitor updated", competitor)


@router.delete("/{competitor_id}")
def remove_competitor(competitor_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    delete_competitor(db, user["userId"], competitor_id)
    return ok("Competitor deleted", None)
