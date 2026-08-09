import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import AIOTracking, Keyword, RankResult, TrackedKeyword
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

    aio_map = {}
    tracks = db.scalars(
        select(AIOTracking).where(AIOTracking.projectId == project_id)
    ).all()
    for track in tracks:
        aio_map[track.keywordText] = {
            "hasAIOverview": track.hasAIOverview,
            "checkedAt": track.checkedAt.isoformat() if track.checkedAt else None,
        }

    tracked_aio_map = {}
    tracked_rows = db.scalars(
        select(TrackedKeyword).where(TrackedKeyword.userId == user_id, TrackedKeyword.isActive == True)
    ).all()
    for row in tracked_rows:
        tracked_aio_map[row.keyword] = row.trackAio

    results = []
    for kw in keywords:
        keyword_text = kw.keyword
        rank_info = latest_ranks.get(keyword_text, {})
        aio_info = aio_map.get(keyword_text, {})
        track_aio = tracked_aio_map.get(keyword_text, False)
        has_ai_overview = aio_info.get("hasAIOverview", False) or kw.ai_badge == "AIO"

        if has_ai_overview:
            ai = "AIO"
        elif track_aio:
            ai = "Tracking"
        else:
            ai = "Off"

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
            "ai": ai,
            "hasAIOverview": has_ai_overview,
            "aioCheckedAt": aio_info.get("checkedAt"),
            "trackAio": track_aio,
            "visibility": kw.visibility,
            "createdAt": kw.createdAt.isoformat() if getattr(kw, "createdAt", None) else None,
        })

    return results
