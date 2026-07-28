"""
Competitor Alert Service
Monitors competitor rankings and sends alerts when they outrank you
"""
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.errors import ApiError
from app.db.models import Competitor, Project, Keyword, RankResult, User
from app.services.competitor_ranking_service import get_competitor_rank_comparison
from app.services.notification_service import create_competitor_alert_notification
from app.utils.serializers import model_to_dict


def check_competitor_outranking(
    db: Session, 
    user_id: str, 
    project_id: str,
    alert_threshold: int = 5  # Alert if competitor is within 5 positions
) -> List[dict]:
    """
    Check if any competitors are outranking you and create alerts
    Returns list of alerts created
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ApiError(404, "Project not found")
    
    # Check if user has competitor alerts enabled
    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.competitorAlerts:
        return []
    
    # Get competitor comparison data
    comparison = get_competitor_rank_comparison(db, user_id, project_id)
    
    alerts_created = []
    
    for comp_data in comparison:
        competitor_id = comp_data["competitor_id"]
        competitor_name = comp_data["competitor_name"]
        competitor_domain = comp_data["competitor_domain"]
        
        for ranking in comp_data["rankings"]:
            your_position = ranking["your_position"]
            competitor_position = ranking["competitor_position"]
            keyword = ranking["keyword"]
            
            # Only alert if competitor is significantly ahead
            if (your_position and competitor_position and 
                competitor_position < your_position and
                (your_position - competitor_position) <= alert_threshold):
                
                # Check if we already alerted for this recently (avoid spam)
                recent_alert = db.scalar(
                    select(RankResult).where(
                        RankResult.projectId == project_id,
                        RankResult.keywordText == keyword
                    ).order_by(desc(RankResult.checkedAt)).limit(1)
                )
                
                # Only create alert if this is a new situation
                if recent_alert:
                    # Check if we've already created an alert for this in the last 24 hours
                    from app.db.models import Notification
                    existing_alert = db.scalar(
                        select(Notification).where(
                            Notification.userId == user_id,
                            Notification.projectId == project_id,
                            Notification.type == "COMPETITOR_ALERT",
                            Notification.entityId == competitor_domain,
                            Notification.createdAt >= datetime.utcnow() - timedelta(hours=24)
                        )
                    )
                    
                    if existing_alert:
                        continue  # Skip, already alerted recently
                
                # Create the alert
                notification = create_competitor_alert_notification(
                    db,
                    user_id=user_id,
                    project_id=project_id,
                    competitor_name=competitor_name,
                    competitor_domain=competitor_domain,
                    keyword=keyword,
                    your_position=your_position,
                    competitor_position=competitor_position
                )
                
                try:
                    from app.services.notification_service import send_competitor_alert_email
                    send_competitor_alert_email(
                        db,
                        user_id=user_id,
                        competitor_name=competitor_name,
                        keyword=keyword,
                        your_position=your_position,
                        competitor_position=competitor_position,
                    )
                except Exception:
                    pass
                
                alerts_created.append({
                    "competitor": competitor_name,
                    "keyword": keyword,
                    "your_position": your_position,
                    "competitor_position": competitor_position,
                    "gap": your_position - competitor_position
                })
    
    return alerts_created


def get_competitor_alert_settings(
    db: Session, 
    user_id: str
) -> dict:
    """Get user's competitor alert settings"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")
    
    return {
        "competitorAlerts": user.competitorAlerts,
        "dailyKeywordMovement": user.dailyKeywordMovement,
        "weeklyAuditSummary": user.weeklyAuditSummary
    }


def update_competitor_alert_settings(
    db: Session, 
    user_id: str,
    competitorAlerts: Optional[bool] = None,
    dailyKeywordMovement: Optional[bool] = None,
    weeklyAuditSummary: Optional[bool] = None
) -> dict:
    """Update user's notification settings"""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")
    
    if competitorAlerts is not None:
        user.competitorAlerts = competitorAlerts
    if dailyKeywordMovement is not None:
        user.dailyKeywordMovement = dailyKeywordMovement
    if weeklyAuditSummary is not None:
        user.weeklyAuditSummary = weeklyAuditSummary
    
    db.commit()
    db.refresh(user)
    
    return {
        "competitorAlerts": user.competitorAlerts,
        "dailyKeywordMovement": user.dailyKeywordMovement,
        "weeklyAuditSummary": user.weeklyAuditSummary
    }


def run_competitor_alert_check_for_project(db: Session, project_id: str) -> dict:
    """
    Run competitor alert check for a specific project (called by scheduled job)
    """
    from app.db.models import Project
    
    project = db.scalar(select(Project).where(Project.id == project_id))
    if not project:
        return {"error": "Project not found"}
    
    try:
        alerts = check_competitor_outranking(
            db, 
            user_id=project.userId, 
            project_id=project_id
        )
        
        return {
            "project_id": project_id,
            "alerts_created": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        return {
            "project_id": project_id,
            "error": str(e),
            "alerts_created": 0
        }


def run_competitor_alerts_for_all_projects(db: Session) -> dict:
    """
    Run competitor alert checks for all projects (called by scheduled job)
    """
    from app.db.models import Project
    
    projects = db.scalars(select(Project)).all()
    
    total_alerts = 0
    results = []
    
    for project in projects:
        result = run_competitor_alert_check_for_project(db, project.id)
        results.append(result)
        total_alerts += result.get("alerts_created", 0)
    
    return {
        "projects_checked": len(projects),
        "total_alerts_created": total_alerts,
        "results": results
    }
