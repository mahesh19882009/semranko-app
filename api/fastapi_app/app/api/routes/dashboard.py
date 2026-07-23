from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.services.dashboard_service import get_project_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{project_id}")
def get_dashboard(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    data = get_project_dashboard(db, user["userId"], project_id)
    return {"success": True, "message": "Dashboard fetched", "data": data}
