import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, Keyword, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_project_limit, get_user_plan_limits_by_id, ensure_keyword_limit, count_user_keywords
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def create_project_with_keywords(db: Session, user_id: str, name: str, domain: str, location_code: int, location: str, keywords: list[str]) -> Project:
    ensure_project_limit(db, user_id)

    limits = get_user_plan_limits_by_id(db, user_id)
    keyword_limit = limits.get("keywordLimit", 0)
    current_count = count_user_keywords(db, user_id)
    if keyword_limit > 0 and current_count + len(keywords) > keyword_limit:
        raise ApiError(403, f"Keyword limit reached. Your current plan allows {keyword_limit} keywords. You can only add {keyword_limit - current_count} more.")

    project = Project(userId=user_id, name=name, domain=domain)
    db.add(project)
    db.flush()

    for kw in keywords:
        keyword = Keyword(projectId=project.id, userId=user_id, keyword=kw, location=location)
        db.add(keyword)

    db.commit()
    db.refresh(project)
    return project
