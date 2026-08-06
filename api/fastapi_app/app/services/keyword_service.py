import logging
import math
from datetime import datetime, timedelta
from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, KeywordCache
from app.services.plan_service import get_user_or_404
from app.services.dataforseo_client import DataForSEOClient
from app.services.credit_service import deduct_credits
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


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location: str, domain: str) -> bool:
    """
    Fetch DataForSEO data for a newly added keyword and update Keyword + KeywordCache.

    Returns True if data was fetched from API (and credits charged), False if
    served from cache or no data fetched.  Raises on failure so callers can
    refund / show an error.
    """
    try:
        cached = _get_cached_keyword_data(db, keyword_text, location)
        if cached:
            keyword_row = db.scalar(
                select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
            )
            if keyword_row:
                _update_keyword_from_data(keyword_row, cached)
                _update_or_create_cache(db, keyword_text, location, cached)
                db.commit()
            return False

        helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
        rows = helper.fetch_cheapest_dashboard_data(
            [keyword_text],
            domain,
            location_code=2840,
            language_code="en",
        )

        if not rows:
            logger.warning("Day-one tracking: no data returned from DataForSEO for %s", keyword_text)
            return False

        row = rows[0]
        if not _is_cache_data_valid(row):
            logger.warning("Day-one tracking: DataForSEO returned empty data for %s, skipping charge", keyword_text)
            _update_or_create_cache(db, keyword_text, location, row)
            db.commit()
            return False

        owner_id = get_team_owner_id(db, user_id)
        deduct_credits(db, owner_id, 25, "ON_DEMAND_ADD", f"Day-one tracking: {keyword_text}")

        keyword_row = db.scalar(
            select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
        )
        if keyword_row:
            _update_keyword_from_data(keyword_row, row)
        _update_or_create_cache(db, keyword_text, location, row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def _update_or_create_cache(db: Session, keyword_text: str, location: str, data: dict) -> None:
    """Update or create a KeywordCache row from fetched API data."""
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword_text,
            KeywordCache.location == location,
        )
    )
    if cache_entry:
        cache_entry.volume = data.get("volume")
        cache_entry.kd = data.get("kd")
        cache_entry.cpc = data.get("cpc")
        cache_entry.competition = data.get("competition")
        cache_entry.backlinks = data.get("backlinks")
        cache_entry.referring_domains = data.get("referring_domains")
        cache_entry.intent = data.get("intent")
        cache_entry.position = data.get("position")
        cache_entry.ai_badge = data.get("ai_badge")
        cache_entry.lastApiCallAt = datetime.utcnow()
        cache_entry.updatedAt = datetime.utcnow()
    else:
        cache_entry = KeywordCache(
            keyword=keyword_text,
            location=location,
            volume=data.get("volume"),
            kd=data.get("kd"),
            cpc=data.get("cpc"),
            competition=data.get("competition"),
            backlinks=data.get("backlinks"),
            referring_domains=data.get("referring_domains"),
            intent=data.get("intent"),
            position=data.get("position"),
            ai_badge=data.get("ai_badge"),
            lastApiCallAt=datetime.utcnow(),
            updatedAt=datetime.utcnow(),
        )
        db.add(cache_entry)


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

    db.commit()

    if added:
        keywords_to_fetch = []
        cached_keywords = {}
        for kw_text in added:
            cached = _get_cached_keyword_data(db, kw_text, location)
            if cached:
                cached_keywords[kw_text] = cached
                keyword = db.scalar(
                    select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text)
                )
                if keyword:
                    _update_keyword_from_data(keyword, cached)
            else:
                keywords_to_fetch.append(kw_text)

        if keywords_to_fetch:
            helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
            rows = helper.fetch_cheapest_dashboard_data(
                keywords_to_fetch,
                project.domain,
                location_code=2840,
                language_code="en",
            )
            row_map = {row.get("keyword", "").lower().strip(): row for row in rows}

            fetched_ok_count = 0
            for kw_text in keywords_to_fetch:
                keyword = db.scalar(
                    select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text)
                )
                row = row_map.get(kw_text.lower().strip())
                if row and keyword:
                    _update_keyword_from_data(keyword, row)
                    _update_or_create_cache(db, kw_text, location, row)
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