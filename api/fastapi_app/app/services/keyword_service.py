import logging
import math
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


def _apply_day_one_tracking(db: Session, user_id: str, keyword_text: str, location: str, domain: str) -> None:
    try:
        owner_id = get_team_owner_id(db, user_id)
        deduct_credits(db, owner_id, 15, "ON_DEMAND_ADD", f"Day-one tracking: {keyword_text}")

        helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
        dashboard_data = helper.fetch_cheapest_dashboard_data(
            [keyword_text],
            domain,
            location_code=2840,
        )

        if dashboard_data:
            row = dashboard_data[0]
            cache_entry = KeywordCache(
                keyword=keyword_text,
                location=location or "India",
                volume=int(row.get("Search Volume")) if str(row.get("Search Volume", "—")).replace('.', '', 1).isdigit() else None,
                kd=int(row.get("KD")) if str(row.get("KD", "—")).replace('.', '', 1).isdigit() else None,
                intent=row.get("Intent") if row.get("Intent") not in ["—", None] else None,
                cpc=float(row.get("CPC")) if str(row.get("CPC", "—")).replace('.', '', 1).isdigit() else None,
                competition=float(row.get("Competition")) if str(row.get("Competition", "—")).replace('.', '', 1).isdigit() else None,
                backlinks=float(row.get("Backlinks")) if str(row.get("Backlinks", "—")).replace('.', '', 1).isdigit() else None,
                referring_domains=float(row.get("Domains")) if str(row.get("Domains", "—")).replace('.', '', 1).isdigit() else None,
                position=int(row.get("Position")) if str(row.get("Position", "—")).replace('.', '', 1).isdigit() else None,
                ai_badge=row.get("AI") if row.get("AI") == "AIO" else None,
            )
            db.merge(cache_entry)

            keyword_row = db.scalar(
                select(Keyword).where(Keyword.userId == user_id, Keyword.keyword == keyword_text)
            )
            if keyword_row:
                keyword_row.volume = cache_entry.volume
                keyword_row.kd = cache_entry.kd
                keyword_row.cpc = cache_entry.cpc
                keyword_row.competition = cache_entry.competition
                keyword_row.backlinks = cache_entry.backlinks
                keyword_row.referring_domains = cache_entry.referring_domains
                keyword_row.intent = cache_entry.intent
                keyword_row.position = cache_entry.position
                keyword_row.ai_badge = cache_entry.ai_badge
                keyword_row.updatedAt = datetime.utcnow()

            db.commit()
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
        keyword=normalized_keyword,
        location=(payload.get("location") or "India"),
        device=(payload.get("device") or "desktop"),
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    _apply_day_one_tracking(db, user_id, normalized_keyword, keyword.location or "India", project.domain)

    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == normalized_keyword,
            KeywordCache.location == (keyword.location or "India"),
        )
    )
    if cache_entry:
        keyword.volume = cache_entry.volume
        keyword.kd = cache_entry.kd
        keyword.cpc = cache_entry.cpc
        keyword.competition = cache_entry.competition
        keyword.backlinks = cache_entry.backlinks
        keyword.referring_domains = cache_entry.referring_domains
        keyword.intent = cache_entry.intent
        keyword.position = cache_entry.position
        keyword.ai_badge = cache_entry.ai_badge
        db.commit()
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
            keyword=kw,
            location=location,
            device="desktop",
        )
        db.add(keyword)
        added.append(kw)
        existing_set.add(kw)

    if added:
        owner_id_for_check = get_team_owner_id(db, user_id)
        credits_needed = len(added) * 15
        deduct_credits(db, owner_id_for_check, credits_needed, "ON_DEMAND_ADD", f"Day-one tracking: {len(added)} keyword(s)")

    db.commit()

    if added:
        try:
            helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
            dashboard_data = helper.fetch_cheapest_dashboard_data(
                added,
                project.domain,
                location_code=2840,
            )

            data_map = {}
            if dashboard_data:
                for row in dashboard_data:
                    kw = row.get("Keyword")
                    if kw:
                        data_map[kw] = {
                            "volume": int(row.get("Search Volume")) if str(row.get("Search Volume", "—")).replace('.', '', 1).isdigit() else None,
                            "kd": int(row.get("KD")) if str(row.get("KD", "—")).replace('.', '', 1).isdigit() else None,
                            "cpc": float(row.get("CPC")) if str(row.get("CPC", "—")).replace('.', '', 1).isdigit() else None,
                            "competition": float(row.get("Competition")) if str(row.get("Competition", "—")).replace('.', '', 1).isdigit() else None,
                            "backlinks": float(row.get("Backlinks")) if str(row.get("Backlinks", "—")).replace('.', '', 1).isdigit() else None,
                            "referring_domains": float(row.get("Domains")) if str(row.get("Domains", "—")).replace('.', '', 1).isdigit() else None,
                            "intent": row.get("Intent") if row.get("Intent") not in ["—", None] else None,
                            "position": int(row.get("Position")) if str(row.get("Position", "—")).replace('.', '', 1).isdigit() else None,
                            "ai_badge": row.get("AI") if row.get("AI") == "AIO" else None,
                        }

            for kw_text in added:
                data = data_map.get(kw_text)
                if data:
                    cache_entry = KeywordCache(
                        keyword=kw_text,
                        location=location,
                        **data
                    )
                    db.merge(cache_entry)

                    keyword = db.scalar(select(Keyword).where(Keyword.projectId == project_id, Keyword.keyword == kw_text))
                    if keyword:
                        keyword.volume = data.get("volume")
                        keyword.kd = data.get("kd")
                        keyword.cpc = data.get("cpc")
                        keyword.competition = data.get("competition")
                        keyword.backlinks = data.get("backlinks")
                        keyword.referring_domains = data.get("referring_domains")
                        keyword.intent = data.get("intent")

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to fetch keyword metrics for batch: {e}")
            refund_credits(db, owner_id_for_check, credits_needed, f"Refund: day-one tracking failed for batch ({len(added)} keywords)")
            raise

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