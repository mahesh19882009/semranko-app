import logging
import math
import re
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project
from app.services.cache_service import increment_usage
from app.services.credit_service import deduct_credits, refund_credits
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_cache_data_valid(data: dict) -> bool:
    if not data:
        return False
    core_fields = ["volume", "kd", "cpc", "position", "intent"]
    non_null_count = sum(1 for field in core_fields if data.get(field) is not None)
    return non_null_count >= 2


def research_keyword(db: Session, user_id: str, keyword: str, location_code: int = 2840) -> dict:
    from app.services.dataforseo_client import DataForSEOClient
    from app.services.keyword_research_cache_service import query_research_cache, save_research_cache

    cached_ideas = query_research_cache(db, user_id, keyword, location_code)
    if cached_ideas is not None:
        logger.info("Returning cached keyword research for '%s' (location=%s)", keyword, location_code)
        normalized = [_normalize_idea(i) for i in cached_ideas]
        return _build_research_response(keyword, normalized, credits_charged=0)

    ideas = DataForSEOClient.get_keyword_ideas_api(keyword, location_code, limit=50)
    save_research_cache(db, user_id, keyword, location_code, ideas or [])
    return _build_research_response(keyword, ideas or [], credits_charged=1 if ideas else 0)


def _normalize_idea(idea: dict) -> dict:
    idea = dict(idea)
    if "search_volume" in idea and "volume" not in idea:
        idea["volume"] = idea.pop("search_volume")
    if "keyword_difficulty" in idea and "difficulty" not in idea:
        idea["difficulty"] = idea.pop("keyword_difficulty")
    return idea


def _build_research_response(seed_keyword: str, ideas: list[dict], credits_charged: int) -> dict:
    seed_lower = seed_keyword.lower().strip()
    seed_metrics = {
        "volume": None,
        "kd": None,
        "cpc": None,
        "intent": None,
        "competition": None,
    }
    for idea in ideas:
        if idea.get("keyword", "").lower().strip() == seed_lower:
            seed_metrics = {
                "volume": idea.get("volume"),
                "kd": idea.get("difficulty"),
                "cpc": idea.get("cpc"),
                "intent": idea.get("intent"),
                "competition": None,
            }
            break

    return {
        "seed": seed_keyword,
        "ideas": ideas,
        "suggestions": ideas,
        **seed_metrics,
        "credits_charged": credits_charged,
    }


def _apply_day_one_tracking_bulk(db: Session, user_id: str, created: list[Keyword], location_code: int, domain: str) -> None:
    if not created:
        return

    try:
        keywords_to_fetch = [kw.keyword for kw in created]

        fetched_ok_count = 0
        if keywords_to_fetch:
            helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
            rows = helper.fetch_cheapest_dashboard_data(
                keywords_to_fetch,
                domain,
                location_code=location_code,
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
                    ai_description = row.get("ai_description")
                    if isinstance(ai_description, str):
                        ai_description = re.sub(r'\.{3}\s*Read more$', '', ai_description.strip()) or None
                    kw.ai_description = ai_description
                    fetched_ok_count += 1

        if fetched_ok_count:
            deduct_credits(
                db,
                user_id,
                float(fetched_ok_count * 25),
                "ON_DEMAND_ADD",
                f"Day-one tracking: {fetched_ok_count} keyword(s)",
            )

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for batch: {exc}")
        raise


def add_keywords_to_project(db: Session, user_id: str, project_id: str, keywords: list[str], location_code: int = 2840, location: str = "India") -> list[Keyword]:
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

    _apply_day_one_tracking_bulk(db, user_id, created, location_code, project.domain)

    for kw in created:
        db.refresh(kw)
    return created
