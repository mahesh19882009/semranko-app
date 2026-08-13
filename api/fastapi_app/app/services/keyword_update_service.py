"""
Cost-Aware Keyword Update Service

Centralizes all keyword refresh logic:
   1. Check user credits
   2. Determine which keywords need refresh (cache miss or stale)
   3. Split into affordable batch
   4. Choose endpoint based on batch size:
       - 1-50 keywords: SERP live/advanced + Labs overview (sync, immediate)
       - 50+ keywords: SERP task_post async + pingback
   5. Reserve credits before API call, consume on success, refund on failure
   6. Update Keyword
   7. Return summary: updated, skipped, failed, remaining
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import Keyword, Project, CreditLedger
from app.services.credit_service import reserve_credits, consume_reserved, refund_reserved
from app.services.dataforseo_client import DataForSEOClient, LOCATION_MAP
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CREDIT_COST_PER_KEYWORD = settings.plan_config.credit_costs.get("weekly_refresh_per_keyword", 10)
SYNC_BATCH_THRESHOLD = 50
DATAFORSEO_BATCH_LIMIT = 1000
MANUAL_REFRESH_COOLDOWN_MINUTES = 60
MAX_MANUAL_REFRESHES_PER_USER_PER_DAY = 50


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
    4. Reserve credits before API call
    5. Fetch via synchronous live/advanced + Labs overview
    6. Consume reserved credits on success, refund on failure
    7. Update Keyword
    8. Return summary: updated, skipped, failed, remaining
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        return {"success": False, "error": "PROJECT_NOT_FOUND"}

    project_location_code = project.locationCode or LOCATION_MAP.get(project.location or "India", 2840)

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

    now = datetime.utcnow()
    cooldown_cutoff = now - timedelta(minutes=MANUAL_REFRESH_COOLDOWN_MINUTES)
    day_cutoff = now - timedelta(days=1)

    filtered_keywords = []
    for kw in needs_refresh:
        if kw.lastWeeklyRefreshAt and kw.lastWeeklyRefreshAt > cooldown_cutoff:
            skipped += 1
            continue
        filtered_keywords.append(kw)

    needs_refresh = filtered_keywords

    if not needs_refresh:
        return {"success": True, "updated": 0, "skipped": skipped, "failed": 0, "remaining_credits_needed": 0}

    daily_refresh_count = db.scalar(
        select(func.count())
        .select_from(CreditLedger)
        .where(
            CreditLedger.userId == user_id,
            CreditLedger.actionType == "charge",
            CreditLedger.description.like("Keyword refresh:%"),
            CreditLedger.timestamp >= day_cutoff,
        )
    ) or 0

    if daily_refresh_count >= MAX_MANUAL_REFRESHES_PER_USER_PER_DAY:
        return {
            "success": False,
            "error": "DAILY_LIMIT_EXCEEDED",
            "message": f"Daily manual refresh limit exceeded. Maximum {MAX_MANUAL_REFRESHES_PER_USER_PER_DAY} manual refreshes per day.",
            "data": {
                "daily_count": daily_refresh_count,
                "daily_limit": MAX_MANUAL_REFRESHES_PER_USER_PER_DAY,
            },
        }

    estimated_dfs_cost = len(needs_refresh) * 0.037
    from app.services.dataforseo_client import check_dfs_cost_ceiling
    try:
        check_dfs_cost_ceiling(db, user_id, estimated_dfs_cost)
    except Exception as exc:
        return {
            "success": False,
            "error": "DFS_COST_CEILING_EXCEEDED",
            "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
        }

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

    reference = f"refresh:{project_id}:{datetime.utcnow().timestamp()}"
    try:
        reserve_credits(
            db,
            user_id,
            float(affordable_count * CREDIT_COST_PER_KEYWORD),
            "reservation",
            f"Keyword refresh reservation: {affordable_count} keyword(s) for project {project_id}",
            reference=reference,
            project_id=project_id,
        )

        from app.db.models import TrackedKeyword
        aio_keyword_texts = set(
            row.keyword
            for row in db.scalars(
                select(TrackedKeyword).where(
                    TrackedKeyword.userId == user_id,
                    TrackedKeyword.isActive == True,
                    TrackedKeyword.trackAio == True,
                    TrackedKeyword.keyword.in_(keyword_texts),
                )
            ).all()
        )

        rows = DataForSEOClient.fetch_dashboard_data(
            keyword_texts,
            project.domain,
            location_code=project_location_code,
            language_code="en",
            db=db,
            user_id=user_id,
            aio_keyword_texts=aio_keyword_texts,
        )
    except Exception as exc:
        try:
            refund_reserved(
                db,
                user_id,
                reference,
                float(affordable_count * CREDIT_COST_PER_KEYWORD),
                description=f"Refund: keyword refresh failed for project {project_id}",
                project_id=project_id,
            )
        except Exception as refund_exc:
            logger.error(f"Failed to refund reserved credits for keyword refresh: {refund_exc}")
        return {
            "success": False,
            "error": "FETCH_FAILED",
            "message": str(exc),
            "remaining_credits_needed": remaining_credits_needed,
        }

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

    consumed_amount = float(updated * CREDIT_COST_PER_KEYWORD)
    reserved_amount = float(affordable_count * CREDIT_COST_PER_KEYWORD)

    try:
        if consumed_amount > 0:
            consume_reserved(
                db,
                user_id,
                reference,
                consumed_amount,
                action_type="charge",
                description=f"Keyword refresh: {updated} keyword(s) for project {project_id}",
                project_id=project_id,
            )

        refund_amount = reserved_amount - consumed_amount
        if refund_amount > 0:
            refund_reserved(
                db,
                user_id,
                reference,
                refund_amount,
                description=f"Refund: {failed} keyword(s) not updated for project {project_id}",
                project_id=project_id,
            )
    except Exception as exc:
        logger.error(f"Failed to finalize reserved credits for keyword refresh: {exc}")
        try:
            refund_reserved(
                db,
                user_id,
                reference,
                reserved_amount,
                description=f"Refund: keyword refresh finalization failed for project {project_id}",
                project_id=project_id,
            )
        except Exception:
            pass

    db.commit()

    return {
        "success": True,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "remaining_credits_needed": remaining_credits_needed,
    }
