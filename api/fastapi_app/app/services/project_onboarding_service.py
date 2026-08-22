import logging
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import Project, Keyword, User
from app.services.dataforseo_client import DataForSEOClient
from app.services.plan_service import ensure_project_limit, get_user_plan_limits_by_id, ensure_keyword_limit, count_user_keywords
from app.core.errors import ApiError
from app.core.config import get_settings
from app.services.credit_service import reserve_credits, consume_reserved, refund_reserved
from app.services.keyword_identity import normalize_device, normalize_keyword

logger = logging.getLogger(__name__)


def create_project_with_keywords(db: Session, user_id: str, name: str, domain: str, location_code: int, location: str, keywords: list[str]) -> Project:
    ensure_project_limit(db, user_id)

    limits = get_user_plan_limits_by_id(db, user_id)
    keyword_limit = limits.get("keywordLimit", 0)
    current_count = count_user_keywords(db, user_id)
    if keyword_limit > 0 and current_count + len(keywords) > keyword_limit:
        raise ApiError(403, f"Keyword limit reached. Your current plan allows {keyword_limit} keywords. You can only add {keyword_limit - current_count} more.")

    normalized_keywords = list(dict.fromkeys(normalize_keyword(kw) for kw in keywords if kw.strip()))
    device = normalize_device("desktop")
    cost = float(get_settings().plan_config.credit_costs["bulk_keyword_add_per_keyword"]) * len(normalized_keywords)
    reference = f"onboard:{user_id}:{uuid.uuid4().hex}"
    reserve_credits(db, user_id, cost, "keyword_add", "Project onboarding keywords", reference=reference)
    try:
        project = Project(
            userId=user_id,
            name=name,
            domain=domain,
            location=location,
            locationCode=location_code,
            device=device,
        )
        db.add(project)
        db.flush()
        for kw in normalized_keywords:
            db.add(Keyword(
                projectId=project.id,
                userId=user_id,
                keyword=kw,
                location=location,
                locationCode=location_code,
                device=device,
            ))
        db.commit()
        consume_reserved(db, user_id, reference, cost, action_type="keyword_add", description="Project onboarding keywords", project_id=project.id)
        db.refresh(project)
        return project
    except Exception:
        db.rollback()
        refund_reserved(db, user_id, reference, cost, description="Refund: project onboarding failed")
        raise
