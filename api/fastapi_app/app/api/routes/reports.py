import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import List, Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.report_service import generate_csv_report, generate_pdf_report, stream_project_keywords_csv
from app.services import email_service
from app.db.models import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["reports"])


class ExportReportRequest(BaseModel):
    start_date: str
    end_date: str
    export_format: str = "csv"
    email_recipients: List[str] = []

    @field_validator("export_format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        value = value.lower()
        if value not in ("csv", "pdf"):
            raise ValueError("export_format must be 'csv' or 'pdf'")
        return value

    @field_validator("email_recipients")
    @classmethod
    def validate_recipients(cls, value: List[str]) -> List[str]:
        if len(value) > 3:
            raise ValueError("Maximum 3 email recipients allowed")
        return value


def _send_report_email(recipients: List[str], file_bytes: bytes, filename: str, project_id: str) -> None:
    if not recipients or not file_bytes:
        return
    try:
        for recipient in recipients:
            email_service.send_email_with_attachment(
                to_email=recipient,
                subject=f"RankCare Export Report - Project {project_id}",
                html_body=f"<p>Please find attached the exported report for project {project_id}.</p>",
                attachment_bytes=file_bytes,
                attachment_filename=filename,
            )
    except Exception as exc:
        logger.exception("Failed to send report email: %s", exc)


@router.post("/{project_id}/export-report")
async def export_project_report(
    project_id: str,
    request: ExportReportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == current_user["id"])
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if request.export_format == "csv":
        file_bytes = generate_csv_report(project_id, request.start_date, request.end_date)
        filename = f"rankcare-report-{project_id}.csv"
    else:
        file_bytes = generate_pdf_report(project_id, request.start_date, request.end_date)
        filename = f"rankcare-report-{project_id}.pdf"

    if request.email_recipients:
        background_tasks.add_task(
            _send_report_email,
            request.email_recipients,
            file_bytes,
            filename,
            project_id,
        )

    return ok("Report generated", {
        "filename": filename,
        "format": request.export_format,
        "size_bytes": len(file_bytes),
        "email_queued": bool(request.email_recipients),
    })


@router.get("/{project_id}/export-csv")
async def stream_project_csv(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == current_user["id"])
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    csv_stream = stream_project_keywords_csv(db, project_id)
    return StreamingResponse(
        csv_stream,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=project-{project_id}-keywords.csv"},
    )
