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
    from app.services.dataforseo_client import DataForSEOClient

    ideas = DataForSEOClient.get_keyword_ideas_api(keyword, location, limit=50)
    return {
        "seed": keyword,
        "ideas": ideas or [],
        "credits_charged": 1 if ideas else 0,
    }


def _apply_day_one_tracking_bulk(db: Session, user_id: str, created: list[Keyword], location: str, domain: str) -> None:
    if not created:
        return

    try:
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

        fetched_ok_count = 0
        if keywords_to_fetch:
            helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
            rows = helper.fetch_cheapest_dashboard_data(
                keywords_to_fetch,
                domain,
                location_code=2840,
                language_code="en",
            )
            row_map = {row.get("keyword", "").lower().strip(): row for row in rows}

            for kw in created:
                row = row_map.get(kw.keyword.lower().strip())
                if row and _is_cache_data_valid(row):
                    kw.volume = row.get("volume")
                    kw.kd = row.get("kd")
                    kw.cpc = row.get("cpc")
                    kw.intent = row.get("intent")
                    kw.position = row.get("position")
                    kw.ai_badge = row.get("ai_badge")
                    fetched_ok_count += 1

        if fetched_ok_count:
            owner_id = get_team_owner_id(db, user_id)
            deduct_credits(
                db,
                owner_id,
                float(fetched_ok_count * 25),
                "ON_DEMAND_ADD",
                f"Day-one tracking: {fetched_ok_count} keyword(s)",
            )

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for batch: {exc}")
        raise


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
