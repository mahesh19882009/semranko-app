from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.services.report_service import (
    create_project_report,
    delete_all_project_reports,
    delete_single_report,
    get_project_reports,
    get_single_report,
)
from app.core.security import enforce_limits

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/detail/{report_id}")
def get_report_by_id(report_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    report = get_single_report(db, user["userId"], report_id)
    return {"success": True, "message": "Report fetched successfully", "data": report}


@router.get("/{project_id}")
def list_reports(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    reports = get_project_reports(db, user["userId"], project_id)
    return {"success": True, "message": "Reports fetched successfully", "data": reports}


@router.post("/{project_id}/run")
@enforce_limits(resource_type='report')
def create_report(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> JSONResponse:
    report = create_project_report(db, user["userId"], project_id)
    return JSONResponse(status_code=201, content={"success": True, "message": "Report generated successfully", "data": report})


@router.delete("/detail/{report_id}")
def delete_report(report_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    deleted = delete_single_report(db, user["userId"], report_id)
    return {"success": True, "message": "Report deleted successfully", "data": deleted}


@router.delete("/{project_id}/all")
def delete_all_reports(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    result = delete_all_project_reports(db, user["userId"], project_id)
    return {"success": True, "message": "All reports deleted successfully", "data": result}
