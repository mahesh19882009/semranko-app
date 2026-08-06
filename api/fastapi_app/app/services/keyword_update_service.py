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
  6. Update KeywordCache
  7. Return summary: updated, skipped, failed, remaining
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Keyword, KeywordCache, Project
from app.services.credit_service import deduct_credits
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.team_service import get_team_owner_id
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CREDIT_COST_PER_KEYWORD = settings.USER_CREDIT_COSTS.get("weekly_refresh_per_keyword", 10)
CACHE_TTL_DAYS = 7
SYNC_BATCH_THRESHOLD = 50
DATAFORSEO_BATCH_LIMIT = 1000
REFRESH_STALE_DAYS = 6


def _get_stale_cutoff() -> datetime:
    return datetime.utcnow() - timedelta(days=REFRESH_STALE_DAYS)


def _needs_refresh(cache_entry: Optional[KeywordCache], force: bool) -> bool:
    if force:
        return True
    if not cache_entry or not cache_entry.lastApiCallAt:
        return True
    return cache_entry.lastApiCallAt < _get_stale_cutoff()


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
    6. Update KeywordCache
    7. Return summary: updated, skipped, failed, remaining
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        return {"success": False, "error": "PROJECT_NOT_FOUND"}

    owner_id = get_team_owner_id(db, user_id)
    from app.db.models import User
    owner = db.scalar(select(User).where(User.id == owner_id))
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

    needs_refresh = []
    skipped = 0
    for kw in keywords:
        cache_entry = db.scalar(
            select(KeywordCache).where(
                KeywordCache.keyword == kw.keyword,
                KeywordCache.location == (kw.location or "India"),
            )
        )
        if _needs_refresh(cache_entry, force):
            needs_refresh.append(kw)
        else:
            skipped += 1

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
    rows = helper.fetch_cheapest_dashboard_data(
        keyword_texts,
        project.domain,
        location_code=2840,
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
            _update_keyword_from_data(kw, row)
            cache_entry = db.scalar(
                select(KeywordCache).where(
                    KeywordCache.keyword == kw.keyword,
                    KeywordCache.location == kw.location or "India",
                )
            )
            if cache_entry:
                cache_entry.volume = row.get("volume")
                cache_entry.kd = row.get("kd")
                cache_entry.cpc = row.get("cpc")
                cache_entry.competition = row.get("competition")
                cache_entry.backlinks = row.get("backlinks")
                cache_entry.referring_domains = row.get("referring_domains")
                cache_entry.intent = row.get("intent")
                cache_entry.position = row.get("position")
                cache_entry.ai_badge = row.get("ai_badge")
                cache_entry.lastApiCallAt = now
                cache_entry.updatedAt = now
            else:
                cache_entry = KeywordCache(
                    keyword=kw.keyword,
                    location=kw.location or "India",
                    volume=row.get("volume"),
                    kd=row.get("kd"),
                    cpc=row.get("cpc"),
                    competition=row.get("competition"),
                    backlinks=row.get("backlinks"),
                    referring_domains=row.get("referring_domains"),
                    intent=row.get("intent"),
                    position=row.get("position"),
                    ai_badge=row.get("ai_badge"),
                    lastApiCallAt=now,
                    updatedAt=now,
                )
                db.add(cache_entry)
            updated += 1
        else:
            failed += 1

    if updated:
        deduct_credits(
            db,
            owner_id,
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
