from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.services.dashboard_service import get_project_dashboard, get_dashboard_overview
from app.schemas.common import ok

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def get_overview(user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    data = get_dashboard_overview(db, user["userId"])
    return ok("Dashboard overview retrieved", data)


@router.get("/{project_id}")
def get_dashboard(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    data = get_project_dashboard(db, user["userId"], project_id)
    return {"success": True, "message": "Dashboard fetched", "data": data}
