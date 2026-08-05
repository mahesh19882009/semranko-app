import logging
import math
from datetime import datetime, timedelta
from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, KeywordCache
from app.services.plan_service import get_user_or_404
from app.services.dataforseo_client import DataForSEOClient
from app.services.credit_service import deduct_credits, refund_credits
from app.services.team_service import get_team_owner_id
from app.utils.serializers import model_to_dict
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_cache_data_valid(data: dict) -> bool:
    if not data:
        return False
    core_fields = ["volume", "kd", "cpc", "position", "intent"]
    return any(data.get(field) is not None for field in core_fields)


def _get_cached_keyword_data(db: Session, keyword_text: str, location: str) -> dict | None:
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword_text,
            KeywordCache.location == location,
        )
    )
    if not cache_entry:
        return None

    if cache_entry.updatedAt and cache_entry.updatedAt >= datetime.utcnow() - timedelta(days=7):
        data = {
            "volume": cache_entry.volume,
            "kd": cache_entry.kd,
            "cpc": cache_entry.cpc,
            "competition": cache_entry.competition,
            "backlinks": cache_entry.backlinks,
            "referring_domains": cache_entry.referring_domains,
            "intent": cache_entry.intent,
            "position": cache_entry.position,
            "ai_badge": cache_entry.ai_badge,
        }
        if _is_cache_data_valid(data):
            return data
    return None


def _update_keyword_from_data(keyword_row: Keyword, data: dict) -> None:
    keyword_row.volume = data.get("volume")
    keyword_row.kd = data.get("kd")
    keyword_row.cpc = data.get("cpc")
    keyword_row.competition = data.get("competition")
    keyword_row.backlinks = data.get("backlinks")
    keyword_row.referring_domains = data.get("referring_domains")
    keyword_row.intent = data.get("intent")
    keyword_row.position = data.get("position")
    keyword_row.ai_badge = data.get("ai_badge")
    keyword_row.updatedAt = datetime.utcnow()


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location: str, domain: str) -> None:
    try:
        owner_id = get_team_owner_id(db, user_id)
        deduct_credits(db, owner_id, 15, "ON_DEMAND_ADD", f"Day-one tracking: {keyword_text}")
        db.commit()

        cached = _get_cached_keyword_data(db, keyword_text, location)
        if cached:
            keyword_row = db.scalar(
                select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
            )
            if keyword_row:
                _update_keyword_from_data(keyword_row, cached)
                db.commit()
            return

        pingback_url = settings.PINGBACK_URL or f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"
        helper = DataForSeoDashboardHelper()
        helper.fetch_cheapest_dashboard_data(
            [keyword_text],
            domain,
            location_code=2840,
            pingback_url=pingback_url,
            user_id=user_id,
            project_id=None,
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for {keyword_text}: {exc}")
        refund_credits(db, owner_id, 15, f"Refund: day-one tracking failed for {keyword_text}")


def add_keyword(db: Session, user_id: str, project_id: str, payload: dict) -> dict:
    keyword_text = payload.get("keyword")

    if not keyword_text:
        raise ApiError(400, "Keyword is required")

    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
        )
    )
    if existing:
        raise ApiError(409, "Keyword already exists for this project")

    keyword = Keyword(
        projectId=project_id,
        userId=user_id,
        keyword=normalized_keyword,
        location=(payload.get("location") or "India"),
        device=(payload.get("device") or "desktop"),
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
    db.commit()
    db.refresh(keyword)

    _apply_day_one_tracking(db, user_id, normalized_keyword, keyword.location or "India", project.domain)

    db.refresh(keyword)
    return model_to_dict(keyword)


def get_project_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()
    return [model_to_dict(keyword) for keyword in keywords]


def add_keywords_bulk(db: Session, user_id: str, project_id: str, keywords: list[str], location: str = "India") -> dict:
    project = db.scalar(select(Project).where(Project.id == project_id, Project.userId == user_id))
    if not project:
        raise ApiError(404, "Project not found")

    normalized_keywords = []
    for kw in keywords:
        kw = kw.strip().lower()
        if kw:
            normalized_keywords.append(kw)

    if not normalized_keywords:
        return {"added": 0, "skipped": 0, "keywords": []}

    existing = db.scalars(
        select(Keyword.keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword.in_(normalized_keywords),
        )
    ).all()
    existing_set = set(existing)

    added = []
    for kw in normalized_keywords:
        if kw in existing_set:
            continue

        keyword = Keyword(
            projectId=project_id,
            userId=user_id,
            keyword=kw,
            location=location,
            device="desktop",
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
        added.append(kw)
        existing_set.add(kw)

    if added:
        owner_id_for_check = get_team_owner_id(db, user_id)
        credits_needed = len(added) * 15
        deduct_credits(db, owner_id_for_check, float(credits_needed), "ON_DEMAND_ADD", f"Day-one tracking: {len(added)} keyword(s)")

    db.commit()

    if added:
        owner_id_for_check = get_team_owner_id(db, user_id)
        credits_needed = len(added) * 15
        deduct_credits(db, owner_id_for_check, float(credits_needed), "ON_DEMAND_ADD", f"Day-one tracking: {len(added)} keyword(s)")
        db.commit()

        keywords_to_fetch = []
        for kw_text in added:
            cached = _get_cached_keyword_data(db, kw_text, location)
            if cached:
                keyword = db.scalar(select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text))
                if keyword:
                    _update_keyword_from_data(keyword, cached)
            else:
                keywords_to_fetch.append(kw_text)

        if keywords_to_fetch:
            pingback_url = settings.PINGBACK_URL or f"{settings.FRONTEND_URL}/api/webhooks/dataforseo"
            helper = DataForSeoDashboardHelper()
            helper.fetch_cheapest_dashboard_data(
                keywords_to_fetch,
                project.domain,
                location_code=2840,
                pingback_url=pingback_url,
                user_id=user_id,
                project_id=project_id,
            )

    return {
        "added": len(added),
        "skipped": len(normalized_keywords) - len(added),
        "keywords": added,
    }


def delete_keywords_bulk(db: Session, user_id: str, keyword_ids: list[str]) -> int:
    clean_ids = [str(kid) for kid in keyword_ids if isinstance(kid, (str, int))]
    if not clean_ids:
        return 0

    result = db.execute(
        delete(Keyword)
        .where(Keyword.id.in_(clean_ids))
        .where(Keyword.projectId.in_(
            select(Project.id).where(Project.userId == user_id)
        ))
    )
    db.commit()
    return result.rowcount


def delete_keyword(db: Session, user_id: str, keyword_id: str) -> None:
    if not isinstance(keyword_id, (str, int)):
        raise ApiError(400, "Invalid keyword ID format")

    keyword = db.scalar(
        select(Keyword)
        .join(Project, Project.id == Keyword.projectId)
        .where(Keyword.id == str(keyword_id), Project.userId == user_id)
    )

    if not keyword:
        raise ApiError(404, "Keyword not found")

    db.execute(delete(Keyword).where(Keyword.id == str(keyword_id)))
    db.commit()