import logging
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_keyword_research_limit, get_user_plan_limits
from app.services.cache_service import get_cached, set_cached
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def research_keyword(db: Session, user_id: str, keyword: str, location: str = "India") -> dict:
    cached = get_cached("keyword_research", (keyword, location))
    if cached:
        return cached

    ensure_keyword_research_limit(db, user_id, credits_needed=1)

    data = DataForSEOClient.get_keyword_data(keyword, location, force_refresh=True)
    if not data:
        raise ApiError(502, "DataForSEO keyword research failed. Check API credentials or try again later.")

    from app.services.cache_service import increment_usage
    from datetime import datetime
    month_key = datetime.utcnow().strftime("%Y-%m")
    increment_usage(f"keyword_research:{user_id}:{month_key}")

    set_cached("keyword_research", (keyword, location), data, ttl_seconds=30 * 24 * 60 * 60)
    return data


def add_keywords_to_project(db: Session, user_id: str, project_id: str, keywords: list[str], location: str = "India") -> list[Keyword]:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    limits = get_user_plan_limits_by_id(db, user_id)
    current_count = db.scalar(
        select(func.count()).select_from(Keyword).where(Keyword.projectId == project_id)
    ) or 0

    if current_count + len(keywords) > limits["keywords"]:
        raise ApiError(403, f"Keyword limit exceeded. Plan allows {limits['keywords']} keywords.")

    created = []
    for kw in keywords:
        keyword = Keyword(projectId=project_id, keyword=kw, location=location)
        db.add(keyword)
        created.append(keyword)

    db.commit()
    for kw in created:
        db.refresh(kw)

    if created:
        try:
            batch_data = DataForSEOClient.get_keyword_data_batch(
                [kw.keyword for kw in created],
                location,
                force_refresh=True,
            )
            if batch_data:
                from app.services.cache_service import increment_usage
                from datetime import datetime
                month_key = datetime.utcnow().strftime("%Y-%m")
                increment_usage(f"keyword_research:{user_id}:{month_key}", len(batch_data))

            for kw in created:
                data = batch_data.get(kw.keyword)
                if data:
                    kw.volume = data.get("volume")
                    kw.kd = data.get("difficulty")
                    kw.cpc = data.get("cpc")
                    kw.intent = data.get("intent")
        except Exception as e:
            logger.error(f"Failed to fetch keyword metrics for batch: {e}")

    db.commit()
    for kw in created:
        db.refresh(kw)
    return created
