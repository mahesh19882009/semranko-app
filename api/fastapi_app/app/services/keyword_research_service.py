import logging
import math
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_keyword_research_limit, get_user_plan_limits_by_id
from app.services.cache_service import increment_usage
from app.services.credit_service import check_credits
from app.services.team_service import get_team_owner_id

logger = logging.getLogger(__name__)


def research_keyword(db: Session, user_id: str, keyword: str, location: str = "India") -> dict:
    result = DataForSEOClient.get_keyword_ideas(db, user_id, keyword, location)
    return {
        "seed": result.get("seed", keyword),
        "ideas": result.get("ideas", []),
        "credits_charged": result.get("credits_charged", 30),
    }


def add_keywords_to_project(db: Session, user_id: str, project_id: str, keywords: list[str], location: str = "India") -> list[Keyword]:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ValueError("Project not found")

    limits = get_user_plan_limits_by_id(db, user_id)
    current_count = db.scalar(
        select(func.count()).select_from(Keyword).where(Keyword.projectId == project_id)
    ) or 0

    if current_count + len(keywords) > limits["keywords"]:
        raise ValueError(f"Keyword limit exceeded. Plan allows {limits['keywords']} keywords.")

    created = []
    for kw in keywords:
        keyword = Keyword(projectId=project_id, keyword=kw, location=location)
        db.add(keyword)
        created.append(keyword)

    if created:
        owner_id_for_check = get_team_owner_id(db, user_id)
        credits_needed = 15 * len(created)
        check_credits(db, owner_id_for_check, credits_needed)

    db.commit()
    for kw in created:
        db.refresh(kw)

    if created:
        try:
            metrics = DataForSEOClient.bulk_keyword_lookup(
                db,
                user_id,
                [{"keyword": kw.keyword, "location": location} for kw in created],
            )
            batch_data = {item.get("seed", ""): item for item in metrics.get("results", [])}
            if batch_data:
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
            raise

    db.commit()
    for kw in created:
        db.refresh(kw)
    return created
