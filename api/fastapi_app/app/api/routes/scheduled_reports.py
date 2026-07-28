from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.scheduled_reports_service import (
    create_scheduled_report,
    get_user_scheduled_reports,
    get_scheduled_report,
    update_scheduled_report,
    delete_scheduled_report,
)

router = APIRouter(prefix="/scheduled-reports", tags=["scheduled-reports"])


class CreateScheduledReportRequest(BaseModel):
    project_id: str
    name: str
    frequency: str  # daily, weekly, monthly
    format: str  # pdf, csv
    recipients: str  # comma-separated emails
    start_date: Optional[str] = None  # ISO format date string


class UpdateScheduledReportRequest(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    format: Optional[str] = None
    recipients: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("/create")
async def create_scheduled_report_endpoint(
    request: CreateScheduledReportRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new scheduled report
    """
    try:
        # Parse start_date if provided
        start_date = None
        if request.start_date:
            start_date = datetime.fromisoformat(request.start_date)
        
        report = create_scheduled_report(
            db,
            current_user["id"],
            request.project_id,
            request.name,
            request.frequency,
            request.format,
            request.recipients,
            start_date
        )
        
        return ok("Scheduled report created", {
            "id": report.id,
            "name": report.name,
            "frequency": report.frequency,
            "format": report.format,
            "recipients": report.recipients,
            "isActive": report.isActive,
            "nextSendAt": report.nextSendAt.isoformat() if report.nextSendAt else None,
            "createdAt": report.createdAt.isoformat()
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_scheduled_reports(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    List all scheduled reports for the current user
    """
    reports = get_user_scheduled_reports(db, current_user["id"])
    reports_data = [
        {
            "id": report.id,
            "projectId": report.projectId,
            "name": report.name,
            "frequency": report.frequency,
            "format": report.format,
            "recipients": report.recipients,
            "isActive": report.isActive,
            "lastSentAt": report.lastSentAt.isoformat() if report.lastSentAt else None,
            "nextSendAt": report.nextSendAt.isoformat() if report.nextSendAt else None,
            "createdAt": report.createdAt.isoformat()
        }
        for report in reports
    ]
    
    return ok("Scheduled reports retrieved", {"reports": reports_data})


@router.get("/{report_id}")
async def get_scheduled_report_endpoint(
    report_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific scheduled report
    """
    report = get_scheduled_report(db, report_id, current_user["id"])
    if not report:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    return ok("Scheduled report retrieved", {
        "id": report.id,
        "projectId": report.projectId,
        "name": report.name,
        "frequency": report.frequency,
        "format": report.format,
        "recipients": report.recipients,
        "isActive": report.isActive,
        "lastSentAt": report.lastSentAt.isoformat() if report.lastSentAt else None,
        "nextSendAt": report.nextSendAt.isoformat() if report.nextSendAt else None,
        "createdAt": report.createdAt.isoformat()
    })


@router.put("/{report_id}")
async def update_scheduled_report_endpoint(
    report_id: str,
    request: UpdateScheduledReportRequest,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a scheduled report
    """
    report = update_scheduled_report(
        db,
        report_id,
        current_user["id"],
        request.name,
        request.frequency,
        request.format,
        request.recipients,
        request.is_active
    )
    
    if not report:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    return ok("Scheduled report updated", {
        "id": report.id,
        "name": report.name,
        "frequency": report.frequency,
        "format": report.format,
        "recipients": report.recipients,
        "isActive": report.isActive,
        "nextSendAt": report.nextSendAt.isoformat() if report.nextSendAt else None
    })


@router.delete("/{report_id}")
async def delete_scheduled_report_endpoint(
    report_id: str,
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a scheduled report
    """
    success = delete_scheduled_report(db, report_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    return ok("Scheduled report deleted", {"success": True})
