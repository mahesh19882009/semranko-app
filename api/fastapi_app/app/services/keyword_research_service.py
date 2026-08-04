import logging
import math
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project, KeywordCache
from app.services.keyword_service import _get_cached_keyword_data, _update_keyword_from_data
from app.services.cache_service import increment_usage
from app.services.credit_service import deduct_credits, refund_credits
from app.services.team_service import get_team_owner_id
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def research_keyword(db: Session, user_id: str, keyword: str, location: str = "India") -> dict:
    return {
        "seed": keyword,
        "ideas": [],
        "credits_charged": 0,
    }


def _apply_day_one_tracking_bulk(db: Session, user_id: str, created: list[Keyword], location: str, domain: str) -> None:
    if not created:
        return

    try:
        owner_id = get_team_owner_id(db, user_id)
        credits_needed = len(created) * 15
        deduct_credits(db, owner_id, float(credits_needed), "ON_DEMAND_ADD", f"Day-one tracking: {credits_needed} keyword(s)")
        db.commit()

        keywords_to_fetch = []
        for kw in created:
            cached = _get_cached_keyword_data(db, kw.keyword, location)
            if cached:
                kw.volume = cached.get("volume")
                kw.kd = cached.get("kd")
                kw.cpc = cached.get("cpc")
                kw.intent = cached.get("intent")
                kw.position = cached.get("position")
                kw.ai_badge = cached.get("ai_badge")
            else:
                keywords_to_fetch.append(kw.keyword)

        if keywords_to_fetch:
            pingback_url = settings.PINGBACK_URL or f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"
            helper = DataForSeoDashboardHelper()
            helper.fetch_cheapest_dashboard_data(
                keywords_to_fetch,
                domain,
                location_code=2840,
                pingback_url=pingback_url,
                user_id=user_id,
                project_id=None,
            )
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for batch: {exc}")
        refund_credits(db, owner_id, float(credits_needed), f"Refund: day-one tracking failed for batch ({len(created)} keywords)")


def add_keywords_to_project(db: Session, user_id: str, project_id: str, keywords: list[str], location: str = "India") -> list[Keyword]:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ValueError("Project not found")

    created = []
    for kw in keywords:
        keyword = Keyword(
            projectId=project_id,
            userId=user_id,
            keyword=kw,
            location=location,
            isActive=True,
            volume=0,
            kd=0,
            cpc=0.0,
            competition=0.0,
            backlinks=0.0,
            referring_domains=0.0,
            intent="—",
            position=0,
            ai_badge="—",
        )
        db.add(keyword)
        created.append(keyword)

    db.commit()
    for kw in created:
        db.refresh(kw)

    _apply_day_one_tracking_bulk(db, user_id, created, location, project.domain)

    for kw in created:
        db.refresh(kw)
    return created
