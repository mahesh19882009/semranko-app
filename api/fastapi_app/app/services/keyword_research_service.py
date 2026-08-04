import logging
import math
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.models import Keyword, Project, KeywordCache
from app.services.cache_service import increment_usage
from app.services.credit_service import deduct_credits, refund_credits
from app.services.team_service import get_team_owner_id
from app.services.dataforseo_dashboard import DataForSeoDashboardHelper
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def research_keyword(db: Session, user_id: str, keyword: str, location: str = "India") -> dict:
    return {
        "seed": keyword,
        "ideas": [],
        "credits_charged": 0,
    }


def _apply_day_one_tracking_bulk(db: Session, user_id: str, created: list[Keyword], location: str, domain: str) -> None:
    if not created:
        return

    try:
        owner_id = get_team_owner_id(db, user_id)
        credits_needed = len(created) * 15
        deduct_credits(db, owner_id, credits_needed, "ON_DEMAND_ADD", f"Day-one tracking: {credits_needed} keyword(s)")

        helper = DataForSeoDashboardHelper(settings.effective_serp_login, settings.effective_serp_key)
        keywords_list = [kw.keyword for kw in created]
        dashboard_data = helper.fetch_cheapest_dashboard_data(
            keywords_list,
            domain,
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

        for kw in created:
            data = data_map.get(kw.keyword)
            if data:
                cache_entry = KeywordCache(
                    keyword=kw.keyword,
                    location=location,
                    **data
                )
                db.merge(cache_entry)

                kw.volume = data.get("volume")
                kw.kd = data.get("kd")
                kw.cpc = data.get("cpc")
                kw.intent = data.get("intent")
                kw.position = data.get("position")
                kw.ai_badge = data.get("ai_badge")

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Day-one tracking failed for batch: {exc}")
        refund_credits(db, owner_id, credits_needed, f"Refund: day-one tracking failed for batch ({len(created)} keywords)")


def add_keywords_to_project(db: Session, user_id: str, project_id: str, keywords: list[str], location: str = "India") -> list[Keyword]:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.userId == user_id)
    )
    if not project:
        raise ValueError("Project not found")

    created = []
    for kw in keywords:
        keyword = Keyword(projectId=project_id, userId=user_id, keyword=kw, location=location, isActive=True)
        db.add(keyword)
        created.append(keyword)

    db.commit()
    for kw in created:
        db.refresh(kw)

    _apply_day_one_tracking_bulk(db, user_id, created, location, project.domain)

    for kw in created:
        db.refresh(kw)
    return created
