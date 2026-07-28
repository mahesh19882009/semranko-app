from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models import ScheduledReport, User, Project
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def create_scheduled_report(
    db: Session,
    user_id: str,
    project_id: str,
    name: str,
    frequency: str,
    format: str,
    recipients: str
) -> ScheduledReport:
    """
    Create a new scheduled report
    """
    # Calculate next send time based on frequency
    next_send_at = calculate_next_send_time(frequency)
    
    report = ScheduledReport(
        userId=user_id,
        projectId=project_id,
        name=name,
        frequency=frequency,
        format=format,
        recipients=recipients,
        isActive=True,
        nextSendAt=next_send_at
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return report


def get_user_scheduled_reports(db: Session, user_id: str) -> List[ScheduledReport]:
    """
    Get all scheduled reports for a user
    """
    return db.execute(
        select(ScheduledReport)
        .where(ScheduledReport.userId == user_id)
        .order_by(ScheduledReport.createdAt.desc())
    ).scalars().all()


def get_scheduled_report(db: Session, report_id: str, user_id: str) -> Optional[ScheduledReport]:
    """
    Get a specific scheduled report
    """
    return db.execute(
        select(ScheduledReport)
        .where(ScheduledReport.id == report_id)
        .where(ScheduledReport.userId == user_id)
    ).scalar_one_or_none()


def update_scheduled_report(
    db: Session,
    report_id: str,
    user_id: str,
    name: Optional[str] = None,
    frequency: Optional[str] = None,
    format: Optional[str] = None,
    recipients: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Optional[ScheduledReport]:
    """
    Update a scheduled report
    """
    report = get_scheduled_report(db, report_id, user_id)
    
    if not report:
        return None
    
    if name is not None:
        report.name = name
    if frequency is not None:
        report.frequency = frequency
        report.nextSendAt = calculate_next_send_time(frequency)
    if format is not None:
        report.format = format
    if recipients is not None:
        report.recipients = recipients
    if is_active is not None:
        report.isActive = is_active
    
    db.commit()
    db.refresh(report)
    
    return report


def delete_scheduled_report(db: Session, report_id: str, user_id: str) -> bool:
    """
    Delete a scheduled report
    """
    report = get_scheduled_report(db, report_id, user_id)
    
    if not report:
        return False
    
    db.delete(report)
    db.commit()
    
    return True


def calculate_next_send_time(frequency: str) -> datetime:
    """
    Calculate the next send time based on frequency
    """
    now = datetime.utcnow()
    
    if frequency == "daily":
        return now + timedelta(days=1)
    elif frequency == "weekly":
        return now + timedelta(weeks=1)
    elif frequency == "monthly":
        return now + timedelta(days=30)
    else:
        return now + timedelta(days=1)  # Default to daily


def get_due_reports(db: Session) -> List[ScheduledReport]:
    """
    Get all reports that are due to be sent
    """
    now = datetime.utcnow()
    
    return db.execute(
        select(ScheduledReport)
        .where(ScheduledReport.isActive == True)
        .where(ScheduledReport.nextSendAt <= now)
    ).scalars().all()


def mark_report_sent(db: Session, report_id: str) -> bool:
    """
    Mark a report as sent and schedule next send
    """
    report = db.execute(
        select(ScheduledReport)
        .where(ScheduledReport.id == report_id)
    ).scalar_one_or_none()
    
    if not report:
        return False
    
    report.lastSentAt = datetime.utcnow()
    report.nextSendAt = calculate_next_send_time(report.frequency)
    
    db.commit()
    
    return True


def generate_report_data(db: Session, project_id: str) -> dict:
    """
    Generate report data for a project
    This is a simplified version - in production, you'd generate actual PDF/CSV
    """
    try:
        # Get project info
        project = db.execute(
            select(Project)
            .where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            return {"error": "Project not found"}
        
        # Get basic stats (simplified)
        from app.db.models import Keyword, RankResult
        
        keyword_count = db.execute(
            select(func.count()).select_from(Keyword).where(Keyword.projectId == project_id)
        ).scalar() or 0
        
        return {
            "project": {
                "name": project.name,
                "domain": project.domain
            },
            "stats": {
                "totalKeywords": keyword_count,
                "generatedAt": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error generating report data: {e}")
        return {"error": str(e)}
