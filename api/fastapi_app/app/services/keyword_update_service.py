"""
Cost-Aware Keyword Update Service

Centralizes all keyword refresh logic:
  1. Check user credits
  2. Determine which keywords need refresh (cache miss or stale)
  3. Split into affordable batch
   4. Choose endpoint based on batch size:
      - 1-50 keywords: SERP live/advanced + Labs overview (sync, immediate)
      - 50+ keywords: SERP task_post async + pingback
5. Deduct credits AFTER confirming API response
6. Update Keyword
7. Return summary: updated, skipped, failed, remaining
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Keyword, Project
from app.services.credit_service import deduct_credits
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CREDIT_COST_PER_KEYWORD = settings.USER_CREDIT_COSTS.get("weekly_refresh_per_keyword", 10)
SYNC_BATCH_THRESHOLD = 50
DATAFORSEO_BATCH_LIMIT = 1000


def refresh_keyword_data(
    db: Session,
    user_id: str,
    project_id: str,
    keyword_ids: Optional[list[str]] = None,
    force: bool = False,
) -> dict:
    """
    Refresh keyword data for a user's project.

    1. Check user credits
    2. Determine which keywords need refresh (cache miss or stale > 6 days)
    3. Split into affordable batch
    4. Fetch via synchronous live/advanced + Labs overview
    5. Deduct credits AFTER confirming API response
     6. Update Keyword
     7. Return summary: updated, skipped, failed, remaining
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        return {"success": False, "error": "PROJECT_NOT_FOUND"}

    from app.db.models import User
    owner = db.scalar(select(User).where(User.id == user_id))
    current_balance = float(getattr(owner, "creditBalance", 0.0) or 0.0) if owner else 0.0

    query = select(Keyword).where(
        Keyword.projectId == project_id,
        Keyword.isActive == True,
    )
    if keyword_ids:
        query = query.where(Keyword.id.in_(keyword_ids))
    keywords = db.scalars(query).all()

    if not keywords:
        return {"success": True, "updated": 0, "skipped": 0, "failed": 0, "remaining_credits_needed": 0}

    needs_refresh = list(keywords)
    skipped = 0

    total_needed = len(needs_refresh) * CREDIT_COST_PER_KEYWORD
    affordable_count = min(len(needs_refresh), int(current_balance // CREDIT_COST_PER_KEYWORD)) if current_balance >= CREDIT_COST_PER_KEYWORD else 0
    remaining_credits_needed = (len(needs_refresh) - affordable_count) * CREDIT_COST_PER_KEYWORD

    if affordable_count == 0:
        return {
            "success": False,
            "error": "INSUFFICIENT_CREDITS",
            "message": f"You need {total_needed} credits to refresh {len(needs_refresh)} keywords. You have {current_balance} credits.",
            "actionable": "Add credits to continue",
            "data": {
                "required": total_needed,
                "available": current_balance,
                "can_process": 0,
            },
        }

    batch = needs_refresh[:affordable_count]
    keyword_texts = [kw.keyword for kw in batch]
    keyword_map = {kw.keyword: kw for kw in batch}

    helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
    project_location_code = getattr(project, "locationCode", None) or 2840
    rows = helper.fetch_cheapest_dashboard_data(
        keyword_texts,
        project.domain,
        location_code=project_location_code,
        language_code="en",
    )

    row_map = {row.get("keyword", "").lower().strip(): row for row in rows}
    now = datetime.utcnow()
    updated = 0
    failed = 0

    from app.services.keyword_service import _update_keyword_from_data

    for kw in batch:
        row = row_map.get(kw.keyword.lower().strip())
        if row:
            _update_keyword_from_data(db, kw, row)
            updated += 1
        else:
            failed += 1

    if updated:
        deduct_credits(
            db,
            user_id,
            float(updated * CREDIT_COST_PER_KEYWORD),
            "ON_DEMAND_REFRESH",
            f"Keyword refresh: {updated} keyword(s) for project {project_id}",
        )

    db.commit()

    return {
        "success": True,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "remaining_credits_needed": remaining_credits_needed,
    }
