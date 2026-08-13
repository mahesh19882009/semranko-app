import logging
import math
import re
from datetime import datetime, timedelta
from sqlalchemy import or_, update, desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project
from app.services.plan_service import get_user_or_404, ensure_keyword_limit, get_user_plan_limits_by_id, count_user_keywords
from app.services.dataforseo_client import DataForSEOClient, LOCATION_MAP
from app.services.credit_service import deduct_credits, reserve_credits, consume_reserved, refund_reserved
from app.utils.serializers import model_to_dict
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_cache_data_valid(data: dict) -> bool:
    if not data:
        return False
    core_fields = ["volume", "kd", "cpc", "position", "intent"]
    non_null_count = sum(1 for field in core_fields if data.get(field) is not None)
    return non_null_count >= 2


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
    ai_description = data.get("ai_description")
    if isinstance(ai_description, str):
        ai_description = re.sub(r'\.{3}\s*Read more$', '', ai_description.strip()) or None
    keyword_row.ai_description = ai_description
    keyword_row.check_url = data.get("check_url")
    keyword_row.updatedAt = datetime.utcnow()


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location_code: int, domain: str, project_id: str | None = None, keyword_id: str | None = None) -> bool:
    """
    Fetch DataForSEO data for a newly added keyword and update Keyword.

    Returns True if data was fetched from API (and credits charged), False if
    no data fetched.  Raises on failure so callers can
    refund / show an error.
    """
    cost = settings.plan_config.credit_costs.get("add_keyword", 20)
    reference = f"dayone:{project_id or user_id}:{keyword_text}:{datetime.utcnow().timestamp()}"
    try:
        reserve_credits(
            db,
            user_id,
            float(cost),
            "reservation",
            f"Day-one tracking reservation: {keyword_text}",
            reference=reference,
            project_id=project_id,
            keyword_id=keyword_id,
        )

        from app.db.models import TrackedKeyword
        aio_keyword_texts = set(
            row.keyword
            for row in db.scalars(
                select(TrackedKeyword).where(
                    TrackedKeyword.userId == user_id,
                    TrackedKeyword.isActive == True,
                    TrackedKeyword.trackAio == True,
                    TrackedKeyword.keyword == keyword_text,
                )
            ).all()
        )

        rows = DataForSEOClient.fetch_dashboard_data(
            [keyword_text],
            domain,
            location_code=location_code,
            language_code="en",
            aio_keyword_texts=aio_keyword_texts,
        )

        if not rows:
            logger.warning("Day-one tracking: no data returned from DataForSEO for %s", keyword_text)
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: no DataForSEO data for {keyword_text}", project_id=project_id, keyword_id=keyword_id)
            return False

        row = rows[0]
        if not _is_cache_data_valid(row):
            logger.warning("Day-one tracking: DataForSEO returned empty data for %s, skipping charge", keyword_text)
            refund_reserved(db, user_id, reference, float(cost), description=f"Refund: empty DataForSEO data for {keyword_text}", project_id=project_id, keyword_id=keyword_id)
            return False

        consume_reserved(
            db,
            user_id,
            reference,
            float(cost),
            action_type="charge",
            description=f"Day-one tracking: {keyword_text}",
            project_id=project_id,
            keyword_id=keyword_id,
        )

        keyword_row = db.scalar(
            select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
        )
        if keyword_row:
            _update_keyword_from_data(db, keyword_row, row)
            keyword_row.lastWeeklyRefreshAt = datetime.utcnow()
            keyword_row.weeklyRefreshStatus = "success"
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

    ensure_keyword_limit(db, user_id)

    normalized_keyword = keyword_text.strip().lower()
    if not normalized_keyword:
        raise ApiError(400, "Keyword is required")

    existing_active = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
            Keyword.isActive == True,
        )
    )
    if existing_active:
        raise ApiError(409, "Keyword already exists for this project")

    existing_deleted = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
            Keyword.isActive == False,
            Keyword.deletedAt.isnot(None),
        ).order_by(Keyword.deletedAt.desc())
    )
    if existing_deleted:
        cooldown_days = 30
        deleted_at = existing_deleted.deletedAt
        if deleted_at:
            days_since_deletion = (datetime.utcnow() - deleted_at).days
            if days_since_deletion < cooldown_days:
                remaining = cooldown_days - days_since_deletion
                raise ApiError(
                    403,
                    f"Keyword was recently deleted. You can re-add it in {remaining} day(s).",
                )
        db.delete(existing_deleted)
        db.commit()

    existing_deactivated = db.scalar(
        select(Keyword).where(
            Keyword.projectId == project_id,
            Keyword.keyword == normalized_keyword,
            Keyword.isActive == False,
            Keyword.deletedAt.is_(None),
        )
    )
    if existing_deactivated:
        existing_deactivated.isActive = True
        existing_deactivated.updatedAt = datetime.utcnow()
        db.add(existing_deactivated)
        db.commit()
        db.refresh(existing_deactivated)
        _apply_day_one_tracking(db, user_id, normalized_keyword, LOCATION_MAP.get(existing_deactivated.location or "India", 2840), project.domain, project_id=project_id, keyword_id=existing_deactivated.id)
        db.refresh(existing_deactivated)
        return model_to_dict(existing_deactivated)

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

    _apply_day_one_tracking(db, user_id, normalized_keyword, LOCATION_MAP.get(keyword.location or "India", 2840), project.domain, project_id=project_id, keyword_id=keyword.id)

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

    ensure_keyword_limit(db, user_id)

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
        limits = get_user_plan_limits_by_id(db, user_id)
        keyword_limit = limits.get("keywordLimit", 0)
        current_count = db.scalar(
            select(func.count())
            .select_from(Keyword)
            .join(Project, Keyword.projectId == Project.id)
            .where(Project.userId == user_id)
            .where(or_(Keyword.isActive == True, Keyword.deletedAt.is_(None)))
        ) or 0
        if keyword_limit > 0 and current_count + len(added) > keyword_limit:
            raise ApiError(403, f"Keyword limit reached. Your current plan allows {keyword_limit} keywords. You can only add {keyword_limit - current_count} more.")

    db.commit()

    if added:
        keywords_to_fetch = []
        for kw_text in added:
            keywords_to_fetch.append(kw_text)

        if keywords_to_fetch:
            bulk_cost = settings.plan_config.credit_costs.get("bulk_add_keyword", 20)
            total_reserve = float(len(keywords_to_fetch) * bulk_cost)
            bulk_reference = f"bulkdayone:{project_id}:{datetime.utcnow().timestamp()}"
            try:
                reserve_credits(
                    db,
                    user_id,
                    total_reserve,
                    "reservation",
                    f"Bulk day-one tracking reservation: {len(keywords_to_fetch)} keyword(s) for project {project_id}",
                    reference=bulk_reference,
                    project_id=project_id,
                )
            except Exception as exc:
                logger.error(f"Bulk day-one tracking credit reservation failed: {exc}")
                for kw_text in keywords_to_fetch:
                    failed = db.scalar(select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text))
                    if failed:
                        db.delete(failed)
                db.commit()
                raise ApiError(402, f"Insufficient credits for bulk day-one tracking. Required: {total_reserve}")

            from app.db.models import TrackedKeyword
            aio_keyword_texts = set(
                row.keyword
                for row in db.scalars(
                    select(TrackedKeyword).where(
                        TrackedKeyword.userId == user_id,
                        TrackedKeyword.isActive == True,
                        TrackedKeyword.trackAio == True,
                        TrackedKeyword.keyword.in_(keywords_to_fetch),
                    )
                ).all()
            )

            try:
                rows = DataForSEOClient.fetch_dashboard_data(
                    keywords_to_fetch,
                    project.domain,
                    location_code=location_code,
                    language_code="en",
                    aio_keyword_texts=aio_keyword_texts,
                )
            except Exception as exc:
                try:
                    refund_reserved(db, user_id, bulk_reference, total_reserve, description=f"Refund: bulk day-one tracking failed for project {project_id}", project_id=project_id)
                except Exception as refund_exc:
                    logger.error(f"Failed to refund reserved credits for bulk day-one tracking: {refund_exc}")
                raise

            row_map = {row.get("keyword", "").lower().strip(): row for row in rows}

            fetched_ok_count = 0
            for kw_text in keywords_to_fetch:
                keyword = db.scalar(
                    select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text)
                )
                row = row_map.get(kw_text.lower().strip())
                if row and keyword:
                    _update_keyword_from_data(db, keyword, row)
                    keyword.lastWeeklyRefreshAt = datetime.utcnow()
                    keyword.weeklyRefreshStatus = "success"
                    fetched_ok_count += 1

            consumed_amount = float(fetched_ok_count * bulk_cost)
            refund_amount = total_reserve - consumed_amount

            try:
                if consumed_amount > 0:
                    consume_reserved(
                        db,
                        user_id,
                        bulk_reference,
                        consumed_amount,
                        action_type="charge",
                        description=f"Bulk day-one tracking: {fetched_ok_count} keyword(s) for project {project_id}",
                        project_id=project_id,
                    )

                if refund_amount > 0:
                    refund_reserved(
                        db,
                        user_id,
                        bulk_reference,
                        refund_amount,
                        description=f"Refund: {len(keywords_to_fetch) - fetched_ok_count} keyword(s) not fetched for project {project_id}",
                        project_id=project_id,
                    )
            except Exception as exc:
                logger.error(f"Failed to finalize reserved credits for bulk day-one tracking: {exc}")
                try:
                    refund_reserved(db, user_id, bulk_reference, total_reserve, description=f"Refund: bulk day-one tracking finalization failed for project {project_id}", project_id=project_id)
                except Exception:
                    pass

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

    now = datetime.utcnow()
    db.execute(
        update(Keyword)
        .where(Keyword.id.in_(clean_ids))
        .where(Keyword.projectId.in_(user_project_ids))
        .values(isActive=False, deletedAt=now)
    )
    db.commit()
    logger.info("Bulk delete soft_deleted=%s", existing_count)
    return existing_count


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

    keyword.isActive = False
    keyword.deletedAt = datetime.utcnow()
    db.add(keyword)
    db.commit()
