import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import AIOTracking, Keyword, KeywordCache, RankResult, TrackedKeyword
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def get_enriched_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id, Keyword.isActive == True)
    ).all()

    keyword_strings = [kw.keyword for kw in keywords if kw.keyword]

    cache_rows = db.scalars(
        select(KeywordCache).where(KeywordCache.keyword.in_(keyword_strings))
    ).all()
    cache_map = {row.keyword: row for row in cache_rows}

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
        cache = cache_map.get(keyword_text)
        rank_info = latest_ranks.get(keyword_text, {})
        aio_info = aio_map.get(keyword_text, {})
        track_aio = tracked_aio_map.get(keyword_text, False)
        has_ai_overview = aio_info.get("hasAIOverview", False)

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
            "volume": kw.volume if kw.volume is not None else (cache.volume if cache else None),
            "kd": kw.kd if kw.kd is not None else (cache.kd if cache else None),
            "cpc": kw.cpc if kw.cpc is not None else (cache.cpc if cache else None),
            "competition": kw.competition if kw.competition is not None else (cache.competition if cache else None),
            "backlinks": kw.backlinks if kw.backlinks is not None else (cache.backlinks if cache else None),
            "domains": kw.referring_domains if kw.referring_domains is not None else (cache.referring_domains if cache else None),
            "intent": kw.intent if kw.intent not in (None, "—") else (cache.intent if cache else None),
            "position": kw.position if kw.position is not None else (cache.position if cache else None),
            "url": rank_info.get("url"),
            "rankCheckedAt": rank_info.get("checkedAt"),
            "ai": ai,
            "hasAIOverview": has_ai_overview,
            "aioCheckedAt": aio_info.get("checkedAt"),
            "trackAio": track_aio,
            "createdAt": kw.createdAt.isoformat() if getattr(kw, "createdAt", None) else None,
        })

    return results
