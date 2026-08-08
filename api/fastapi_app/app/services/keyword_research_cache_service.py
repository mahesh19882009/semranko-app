import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KeywordResearchCache

CACHE_TTL_DAYS = 90


def query_research_cache(db: Session, user_id: str, seed_keyword: str, location_code: int) -> list[dict] | None:
    cutoff = datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)
    row = db.scalar(
        select(KeywordResearchCache).where(
            KeywordResearchCache.userId == user_id,
            KeywordResearchCache.seedKeyword == seed_keyword,
            KeywordResearchCache.locationCode == location_code,
            KeywordResearchCache.updatedAt >= cutoff,
        )
    )
    if not row or not row.ideasJson:
        return None
    try:
        return json.loads(row.ideasJson)
    except json.JSONDecodeError:
        return None


def save_research_cache(db: Session, user_id: str, seed_keyword: str, location_code: int, ideas: list[dict]) -> None:
    payload = {"ideasJson": json.dumps(ideas)}
    row = db.scalar(
        select(KeywordResearchCache).where(
            KeywordResearchCache.userId == user_id,
            KeywordResearchCache.seedKeyword == seed_keyword,
            KeywordResearchCache.locationCode == location_code,
        )
    )
    if row:
        for key, value in payload.items():
            setattr(row, key, value)
        row.updatedAt = datetime.utcnow()
        db.add(row)
    else:
        row = KeywordResearchCache(userId=user_id, seedKeyword=seed_keyword, locationCode=location_code, **payload)
        db.add(row)
    db.commit()
