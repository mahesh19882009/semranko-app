import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import AIOTracking, Keyword, RankResult
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def get_enriched_keywords(db: Session, user_id: str, project_id: str) -> list[dict]:
    project_keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()

    latest_ranks = {}
    for kw in project_keywords:
        rank = db.execute(
            select(RankResult.position, RankResult.url, RankResult.checkedAt)
            .where(RankResult.projectId == project_id, RankResult.keywordText == kw.keyword)
            .order_by(RankResult.checkedAt.desc())
            .limit(1)
        ).fetchone()
        latest_ranks[kw.keyword] = {
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

    results = []
    for kw in project_keywords:
        rank_info = latest_ranks.get(kw.keyword, {})
        aio_info = aio_map.get(kw.keyword, {})
        results.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "location": kw.location,
            "device": kw.device,
            "volume": kw.volume,
            "kd": kw.kd,
            "cpc": kw.cpc,
            "competition": kw.competition,
            "backlinks": kw.backlinks,
            "referring_domains": kw.referring_domains,
            "intent": kw.intent,
            "position": rank_info.get("position"),
            "url": rank_info.get("url"),
            "rankCheckedAt": rank_info.get("checkedAt"),
            "hasAIOverview": aio_info.get("hasAIOverview", False),
            "aioCheckedAt": aio_info.get("checkedAt"),
            "createdAt": kw.createdAt.isoformat() if kw.createdAt else None,
        })

    return results
