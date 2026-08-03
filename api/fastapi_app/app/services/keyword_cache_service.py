import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models import KeywordCache

CACHE_TTL_DAYS = 30


def query_cached_keyword(db: Session, keyword: str, location: str) -> dict | None:
    cutoff = datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)
    row = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword,
            KeywordCache.location == location,
            KeywordCache.updatedAt >= cutoff,
        )
    )
    if not row:
        return None
    return {
        "seed": row.keyword,
        "volume": row.volume,
        "difficulty": row.kd,
        "cpc": row.cpc,
        "competition": row.competition,
        "intent": row.intent,
        "backlinks": row.backlinks,
        "referring_domains": row.referring_domains,
        "cached": True,
        "cachedAt": row.updatedAt.isoformat() if row.updatedAt else None,
    }


def save_cached_keyword(db: Session, keyword: str, location: str, data: dict) -> None:
    row = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword,
            KeywordCache.location == location,
        )
    )
    payload = {
        "volume": data.get("volume"),
        "kd": data.get("difficulty"),
        "intent": data.get("intent"),
        "cpc": data.get("cpc"),
        "competition": data.get("competition"),
        "backlinks": data.get("backlinks"),
        "referring_domains": data.get("referring_domains"),
    }
    if row:
        for key, value in payload.items():
            setattr(row, key, value)
        row.updatedAt = func.now()
        db.add(row)
    else:
        row = KeywordCache(keyword=keyword, location=location, **payload)
        db.add(row)
