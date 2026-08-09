import logging
import math
from datetime import datetime, timedelta
from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, AIOTracking
from app.services.plan_service import get_user_or_404
from app.services.dataforseo_client import DataForSEOClient, LOCATION_MAP
from app.services.credit_service import deduct_credits
from app.services.team_service import get_team_owner_id
from app.utils.serializers import model_to_dict
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.services.aio_service import ensure_aio_tracking
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _update_keyword_from_data(db: Session, keyword_row: Keyword, data: dict) -> None:
    keyword_row.volume = data.get("volume")
    keyword_row.kd = data.get("kd")
    keyword_row.cpc = data.get("cpc")
    keyword_row.competition = data.get("competition")
    keyword_row.backlinks = data.get("backlinks")
    keyword_row.referring_domains = data.get("referring_domains")
    keyword_row.intent = data.get("intent")
    keyword_row.position = data.get("position")
    keyword_row.ai_badge = data.get("ai_badge")
    keyword_row.check_url = data.get("check_url")
    keyword_row.updatedAt = datetime.utcnow()

    ai_badge = data.get("ai_badge")
    if ai_badge:
        ensure_aio_tracking(db, keyword_row.projectId, keyword_row.keyword, ai_badge)


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location_code: int, domain: str) -> bool:
    """
    Fetch DataForSEO data for a newly added keyword and update Keyword.

    Returns True if data was fetched from API (and credits charged), False if
    no data fetched.  Raises on failure so callers can
    refund / show an error.
    """
    try:
        helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
        rows = helper.fetch_cheapest_dashboard_data(
            [keyword_text],
            domain,
            location_code=location_code,
            language_code="en",
        )

        if not rows:
            logger.warning("Day-one tracking: no data returned from DataForSEO for %s", keyword_text)
            return False

        row = rows[0]
        if not _is_cache_data_valid(row):
            logger.warning("Day-one tracking: DataForSEO returned empty data for %s, skipping charge", keyword_text)
            return False

        owner_id = get_team_owner_id(db, user_id)
        deduct_credits(db, owner_id, 20, "ON_DEMAND_ADD", f"Day-one tracking: {keyword_text}")

        keyword_row = db.scalar(
            select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
        )
        if keyword_row:
            _update_keyword_from_data(db, keyword_row, row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


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

    _apply_day_one_tracking(db, user_id, normalized_keyword, LOCATION_MAP.get(keyword.location or "India", 2840), project.domain)

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


def add_keywords_bulk(db: Session, user_id: str, project_id: str, keywords: list[str], location: str = "India", location_code: int = 2840) -> dict:
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
        for kw_text in added:
            keywords_to_fetch.append(kw_text)

        if keywords_to_fetch:
            helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
            rows = helper.fetch_cheapest_dashboard_data(
                keywords_to_fetch,
                project.domain,
                location_code=location_code,
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
                    _update_keyword_from_data(db, keyword, row)
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
    if not keyword_ids:
        return 0

    if isinstance(keyword_ids, str):
        keyword_ids = [keyword_ids]
    elif not isinstance(keyword_ids, list):
        return 0

    clean_ids = [str(kid) for kid in keyword_ids if kid is not None]
    if not clean_ids:
        return 0

    user_project_ids = db.scalars(select(Project.id).where(Project.userId == user_id)).all()
    logger.info("Bulk delete: user_id=%s project_ids=%s keyword_ids=%s", user_id, user_project_ids, clean_ids)
    if not user_project_ids:
        return 0

    existing_count = db.scalar(
        select(func.count(Keyword.id)).where(
            Keyword.id.in_(clean_ids),
            Keyword.projectId.in_(user_project_ids)
        )
    )
    logger.info("Bulk delete matching_count=%s", existing_count)

    result = db.execute(
        delete(Keyword)
        .where(Keyword.id.in_(clean_ids))
        .where(Keyword.projectId.in_(user_project_ids))
    )
    db.commit()
    logger.info("Bulk delete deleted=%s", result.rowcount)
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