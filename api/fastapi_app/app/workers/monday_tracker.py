import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import User, Project, Keyword
from app.db.session import SessionLocal
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.credit_service import deduct_credits
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_user_domains(db: Session, user_id: str) -> list[str]:
    projects = db.scalars(select(Project.domain).where(Project.userId == user_id)).all()
    return [d.lower() for d in projects if d]


def run_monday_tracker() -> dict:
    db = SessionLocal()
    try:
        active_subscription_statuses = ["active", "trialing"]
        keywords = db.scalars(
            select(Keyword)
        ).all()

        if not keywords:
            logger.info("Monday tracker: no keywords found")
            return {"scanned_users": 0, "updated_keywords": 0}

        project_ids = {kw.projectId for kw in keywords}
        projects = db.scalars(
            select(Project).where(Project.id.in_(list(project_ids)))
        ).all()
        project_to_user = {p.id: p.userId for p in projects}

        user_ids = {project_to_user.get(kw.projectId) for kw in keywords if kw.projectId in project_to_user}
        users = db.scalars(
            select(User).where(
                User.id.in_(list(user_ids)),
                User.subscriptionStatus.in_(active_subscription_statuses),
            )
        ).all()
        active_user_ids = {u.id for u in users}

        active_keywords_filtered = [kw for kw in keywords if project_to_user.get(kw.projectId) in active_user_ids]

        if not active_keywords_filtered:
            db.commit()
            logger.info("Monday tracker: no active users with valid subscriptions")
            return {"scanned_users": 0, "updated_keywords": 0}

        user_keyword_groups = defaultdict(list)
        for kw in active_keywords_filtered:
            user_id = project_to_user.get(kw.projectId)
            if user_id:
                user_keyword_groups[user_id].append(kw)

        total_deducted = 0
        users_with_insufficient_credits = set()
        eligible_user_keyword_counts = {}

        refresh_cost = settings.USER_CREDIT_COSTS.get("weekly_refresh_per_keyword", 3)

        for user_id, kws in user_keyword_groups.items():
            active_count = len(kws)
            user = db.scalar(select(User).where(User.id == user_id))

            if not user:
                continue

            current_balance = float(getattr(user, "creditBalance", 0.0) or 0.0)
            required = active_count * refresh_cost

            if current_balance < required:
                users_with_insufficient_credits.add(user_id)
                continue

            eligible_user_keyword_counts[user_id] = {
                "owner_id": user_id,
                "count": active_count,
                "required": required,
            }

        db.commit()

        unique_active_keywords = sorted({kw.keyword.lower().strip() for kw in active_keywords_filtered if kw.keyword})

        if not unique_active_keywords:
            logger.info("Monday tracker: no unique active keywords to process")
            return {
                "scanned_users": len(active_user_ids),
                "updated_keywords": 0,
                "total_deducted": total_deducted,
            }

        if unique_active_keywords:
            helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
            target_domain = _get_user_domains(db, list(active_user_ids)[0])[0] if _get_user_domains(db, list(active_user_ids)[0]) else None
            if not target_domain:
                target_domain = "example.com"

            try:
                rows = helper.fetch_cheapest_dashboard_data(
                    unique_active_keywords,
                    target_domain,
                    location_code=2840,
                    language_code="en",
                )
                row_map = {row.get("keyword", "").lower().strip(): row for row in rows}
                now = datetime.utcnow()
                updated = 0
                for kw_text in unique_active_keywords:
                    keyword_row = db.scalar(
                        select(Keyword).where(Keyword.keyword == kw_text)
                    )
                    row = row_map.get(kw_text.lower().strip())
                    if row and keyword_row:
                        keyword_row.volume = row.get("volume")
                        keyword_row.kd = row.get("kd")
                        keyword_row.cpc = row.get("cpc")
                        keyword_row.competition = row.get("competition")
                        keyword_row.backlinks = row.get("backlinks")
                        keyword_row.referring_domains = row.get("referring_domains")
                        keyword_row.intent = row.get("intent")
                        keyword_row.position = row.get("position")
                        keyword_row.ai_badge = row.get("ai_badge")
                        ai_description = row.get("ai_description")
                        if isinstance(ai_description, str):
                            ai_description = re.sub(r'\.{3}\s*Read more$', '', ai_description.strip()) or None
                        keyword_row.ai_description = ai_description
                        keyword_row.updatedAt = now
                        db.add(keyword_row)
                        updated += 1

                # Deduct credits only after successful API response
                for user_id, info in eligible_user_keyword_counts.items():
                    deduct_credits(
                        db,
                        info["owner_id"],
                        float(info["required"]),
                        "WEEKLY_REFRESH",
                        f"Monday weekly refresh: {info['count']} active keyword(s)",
                    )
                    total_deducted += info["required"]
            except Exception as exc:
                logger.error("Monday tracker DataForSEO fetch failed: %s", exc)
                db.rollback()
                raise

        db.commit()
        logger.info(
            "Monday tracker completed: users=%d unique_keywords=%d refreshed=%d deducted=%d",
            len(active_user_ids),
            len(unique_active_keywords),
            updated,
            total_deducted,
        )
        return {
            "scanned_users": len(active_user_ids),
            "updated_keywords": updated,
            "total_deducted": total_deducted,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Monday tracker failed: %s", exc)
        raise
    finally:
        db.close()
