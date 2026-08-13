import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, Project, Competitor, Keyword
from app.db.session import SessionLocal
from app.services.competitor_rank_service import track_competitor_rankings
from app.services.dataforseo_client import DataForSEOClient
from app.services.credit_service import deduct_credits, reserve_credits, consume_reserved, refund_reserved
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def run_monday_tracker() -> dict:
    """
    Monday job: competitor tracking only.
    
    Weekly SERP refresh for keywords is handled by the Sunday bulk job.
    This job preserves the existing competitor tracking functionality.
    """
    db = SessionLocal()
    try:
        users = db.scalars(
            select(User).where(User.subscriptionStatus == "active")
        ).all()
        active_user_ids = {u.id for u in users}

        if not active_user_ids:
            logger.info("Monday competitor tracker: no active users found")
            return {
                "scanned_users": 0,
                "updated_keywords": 0,
                "total_deducted": 0,
                "competitor_tracked": 0,
            }

        projects = db.scalars(
            select(Project).where(Project.userId.in_(list(active_user_ids)))
        ).all()
        if not projects:
            logger.info("Monday competitor tracker: no projects found")
            return {
                "scanned_users": len(active_user_ids),
                "updated_keywords": 0,
                "total_deducted": 0,
                "competitor_tracked": 0,
            }

        competitor_tracked = 0
        for project in projects:
            user_id = project.userId
            if user_id not in active_user_ids:
                continue

            competitors = db.scalars(
                select(Competitor).where(Competitor.projectId == project.id)
            ).all()
            project_keywords = db.scalars(
                select(Keyword).where(Keyword.projectId == project.id, Keyword.isActive == True)
            ).all()

            if not competitors or not project_keywords:
                continue

            try:
                result = track_competitor_rankings(
                    db=db,
                    user_id=user_id,
                    project_id=project.id,
                    depth=10,
                )
                competitor_tracked += result.get("tracked", 0)
            except Exception as exc:
                logger.error(
                    f"Monday competitor tracker failed for user {user_id} project {project.id}: {exc}"
                )

        db.commit()
        logger.info(
            "Monday competitor tracker completed: users=%d competitor_tracked=%d",
            len(active_user_ids),
            competitor_tracked,
        )
        return {
            "scanned_users": len(active_user_ids),
            "updated_keywords": 0,
            "total_deducted": 0,
            "competitor_tracked": competitor_tracked,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Monday competitor tracker failed: %s", exc)
        raise
    finally:
        db.close()


def _calculate_visibility(position):
    if position is None or position > 100:
        return 0.0
    if 1 <= position <= 10:
        return round(1.0 - (position - 1) * 0.1, 2)
    if 11 <= position <= 20:
        return 0.05
    return 0.0
