import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Keyword, RankResult
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def get_enriched_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id, Keyword.isActive == True)
    ).all()

    keyword_strings = [kw.keyword for kw in keywords if kw.keyword]

    latest_ranks = {}
    for kw in keywords:
        keyword_text = kw.keyword
        rank = db.execute(
            select(RankResult.position, RankResult.url, RankResult.checkedAt)
            .where(RankResult.projectId == project_id, RankResult.keywordText == keyword_text)
            .order_by(RankResult.checkedAt.desc())
            .limit(1)
        ).fetchone()
        latest_ranks[keyword_text] = {
            "position": rank[0] if rank else None,
            "url": rank[1] if rank else None,
            "checkedAt": rank[2].isoformat() if rank and rank[2] else None,
        }

    results = []
    for kw in keywords:
        keyword_text = kw.keyword
        rank_info = latest_ranks.get(keyword_text, {})
        has_ai_overview = kw.ai_badge == "AIO"

        results.append({
            "id": kw.id,
            "keyword": keyword_text,
            "location": kw.location or "India",
            "device": kw.device or "desktop",
            "volume": kw.volume,
            "kd": kw.kd,
            "cpc": kw.cpc,
            "competition": kw.competition,
            "backlinks": kw.backlinks,
            "domains": kw.referring_domains,
            "intent": kw.intent,
            "position": kw.position,
            "url": rank_info.get("url"),
            "check_url": kw.check_url,
            "rankCheckedAt": rank_info.get("checkedAt"),
            "ai": "AIO" if has_ai_overview else "Off",
            "hasAIOverview": has_ai_overview,
            "ai_description": kw.ai_description,
            "visibility": kw.visibility,
            "createdAt": kw.createdAt.isoformat() if getattr(kw, "createdAt", None) else None,
        })

    return results
