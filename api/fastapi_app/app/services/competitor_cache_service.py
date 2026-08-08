import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import CompetitorCache

CACHE_TTL_DAYS = 30


def query_cached_competitor(db: Session, domain: str, location: str) -> dict | None:
    cutoff = datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)
    row = db.scalar(
        select(CompetitorCache).where(
            CompetitorCache.domain == domain,
            CompetitorCache.location == location,
            CompetitorCache.updatedAt >= cutoff,
        )
    )
    if not row:
        return None
    keywords = []
    if row.keywordsJson:
        try:
            keywords = json.loads(row.keywordsJson)
        except Exception:
            keywords = []
    return {
        "domain": row.domain,
        "keywords": keywords,
        "cached": True,
        "cachedAt": row.updatedAt.isoformat() if row.updatedAt else None,
    }


def save_cached_competitor(db: Session, domain: str, location: str, keywords: list[dict]) -> None:
    row = db.scalar(
        select(CompetitorCache).where(
            CompetitorCache.domain == domain,
            CompetitorCache.location == location,
        )
    )
    payload = {"keywordsJson": json.dumps(keywords)}
    if row:
        for key, value in payload.items():
            setattr(row, key, value)
        row.updatedAt = datetime.utcnow()
        db.add(row)
    else:
        row = CompetitorCache(domain=domain, location=location, **payload)
        db.add(row)
    db.commit()
