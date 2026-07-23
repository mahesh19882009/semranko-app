from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.services.audit_service import get_project_audits, run_project_audit

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("/{project_id}")
def list_audits(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    audits = get_project_audits(db, user["userId"], project_id)
    return {"success": True, "message": "Audits fetched", "data": audits}


@router.post("/{project_id}/run")
def create_audit(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> JSONResponse:
    result = run_project_audit(db, user["userId"], project_id)
    return JSONResponse(
        status_code=201,
        content={"success": True, "message": "Audit completed successfully", "data": result},
    )
