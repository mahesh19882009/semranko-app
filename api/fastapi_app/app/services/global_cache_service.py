"""
Global Smart Cache Service

This service implements the Global Smart Cache (Deduplication) strategy:
1. Check global KeywordCache table before calling DataForSEO API
2. If multiple users track same keyword/location, call API only once
3. Benefit: Reduces API costs by ~60-80% as user base grows
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import KeywordCache, CompetitorCache, UserCacheUnlock
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache TTL settings
KEYWORD_CACHE_TTL_DAYS = 30  # Cache keyword data for 30 days
COMPETITOR_CACHE_TTL_DAYS = 30  # Cache competitor data for 30 days
RANK_CACHE_FRESHNESS_HOURS = 168  # Rank data considered fresh for 7 days (weekly updates)


def is_cache_fresh(cache_entry: KeywordCache, max_age_hours: int = None) -> bool:
    """
    Check if a cache entry is still fresh.
    For rank tracking, we consider data fresh for 7 days (weekly updates).
    For on-demand features, we use 30-day cache.
    """
    if not cache_entry or not cache_entry.updatedAt:
        return False
    
    max_age = max_age_hours or RANK_CACHE_FRESHNESS_HOURS
    age = datetime.utcnow() - cache_entry.updatedAt
    return age.total_seconds() < (max_age * 3600)


def get_cached_keyword_metrics(
    db: Session,
    keyword: str,
    location: str = "India"
) -> Optional[dict]:
    """
    Get cached keyword metrics from global cache.
    Returns None if not found or stale.
    """
    cutoff = datetime.utcnow() - timedelta(days=KEYWORD_CACHE_TTL_DAYS)
    
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword.lower().strip(),
            KeywordCache.location == location,
            KeywordCache.updatedAt >= cutoff
        )
    )
    
    if not cache_entry:
        return None
    
    return {
        "keyword": cache_entry.keyword,
        "location": cache_entry.location,
        "volume": cache_entry.volume,
        "kd": cache_entry.kd,
        "intent": cache_entry.intent,
        "cpc": cache_entry.cpc,
        "competition": cache_entry.competition,
        "backlinks": cache_entry.backlinks,
        "referring_domains": cache_entry.referring_domains,
        "position": cache_entry.position,
        "ai_badge": cache_entry.ai_badge,
        "cached": True,
        "cached_at": cache_entry.updatedAt.isoformat() if cache_entry.updatedAt else None,
    }


def get_cached_rank_position(
    db: Session,
    keyword: str,
    location: str = "India",
    domain: Optional[str] = None
) -> Optional[dict]:
    """
    Get cached rank position from global cache.
    Only returns data if it's fresh enough for weekly tracking.
    """
    cutoff = datetime.utcnow() - timedelta(hours=RANK_CACHE_FRESHNESS_HOURS)
    
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword.lower().strip(),
            KeywordCache.location == location,
            KeywordCache.updatedAt >= cutoff
        )
    )
    
    if not cache_entry or cache_entry.position is None:
        return None
    
    return {
        "keyword": cache_entry.keyword,
        "location": cache_entry.location,
        "position": cache_entry.position,
        "cached": True,
        "cached_at": cache_entry.updatedAt.isoformat() if cache_entry.updatedAt else None,
    }


def save_keyword_metrics_to_cache(
    db: Session,
    keyword: str,
    location: str,
    metrics: dict
) -> KeywordCache:
    """
    Save keyword metrics to global cache.
    Updates existing entry or creates new one.
    """
    cache_entry = db.scalar(
        select(KeywordCache).where(
            KeywordCache.keyword == keyword.lower().strip(),
            KeywordCache.location == location
        )
    )
    
    now = datetime.utcnow()
    
    if cache_entry:
        # Update existing entry
        cache_entry.volume = metrics.get("volume", cache_entry.volume)
        cache_entry.kd = metrics.get("kd", cache_entry.kd)
        cache_entry.intent = metrics.get("intent", cache_entry.intent)
        cache_entry.cpc = metrics.get("cpc", cache_entry.cpc)
        cache_entry.competition = metrics.get("competition", cache_entry.competition)
        cache_entry.backlinks = metrics.get("backlinks", cache_entry.backlinks)
        cache_entry.referring_domains = metrics.get("referring_domains", cache_entry.referring_domains)
        cache_entry.position = metrics.get("position", cache_entry.position)
        cache_entry.ai_badge = metrics.get("ai_badge", cache_entry.ai_badge)
        cache_entry.updatedAt = now
        cache_entry.lastApiCallAt = now
        db.add(cache_entry)
    else:
        # Create new entry
        cache_entry = KeywordCache(
            keyword=keyword.lower().strip(),
            location=location,
            volume=metrics.get("volume"),
            kd=metrics.get("kd"),
            intent=metrics.get("intent"),
            cpc=metrics.get("cpc"),
            competition=metrics.get("competition"),
            backlinks=metrics.get("backlinks"),
            referring_domains=metrics.get("referring_domains"),
            position=metrics.get("position"),
            ai_badge=metrics.get("ai_badge"),
            lastApiCallAt=now,
            updatedAt=now
        )
        db.add(cache_entry)
    
    db.flush()
    logger.debug(f"Saved keyword cache for '{keyword}' in {location}")
    return cache_entry


def get_cached_competitor_data(
    db: Session,
    domain: str,
    location: str = "India"
) -> Optional[dict]:
    """
    Get cached competitor data from global cache.
    Returns None if not found or stale (>30 days).
    """
    cutoff = datetime.utcnow() - timedelta(days=COMPETITOR_CACHE_TTL_DAYS)
    
    cache_entry = db.scalar(
        select(CompetitorCache).where(
            CompetitorCache.domain == domain.lower().strip(),
            CompetitorCache.location == location,
            CompetitorCache.updatedAt >= cutoff
        )
    )
    
    if not cache_entry:
        return None
    
    keywords = []
    if cache_entry.keywordsJson:
        try:
            keywords = json.loads(cache_entry.keywordsJson)
        except Exception:
            keywords = []
    
    return {
        "domain": cache_entry.domain,
        "location": cache_entry.location,
        "keywords": keywords,
        "cached": True,
        "cached_at": cache_entry.updatedAt.isoformat() if cache_entry.updatedAt else None,
    }


def save_competitor_data_to_cache(
    db: Session,
    domain: str,
    location: str,
    keywords: list[dict]
) -> CompetitorCache:
    """
    Save competitor data to global cache.
    Updates existing entry or creates new one.
    """
    cache_entry = db.scalar(
        select(CompetitorCache).where(
            CompetitorCache.domain == domain.lower().strip(),
            CompetitorCache.location == location
        )
    )
    
    now = datetime.utcnow()
    
    if cache_entry:
        cache_entry.keywordsJson = json.dumps(keywords)
        cache_entry.updatedAt = now
        db.add(cache_entry)
    else:
        cache_entry = CompetitorCache(
            domain=domain.lower().strip(),
            location=location,
            keywordsJson=json.dumps(keywords),
            updatedAt=now
        )
        db.add(cache_entry)
    
    db.flush()
    logger.debug(f"Saved competitor cache for '{domain}' in {location}")
    return cache_entry


def check_user_cache_unlock(
    db: Session,
    owner_id: str,
    target_string: str
) -> bool:
    """
    Check if a user has unlocked access to cached data.
    This is used for team scenarios where one member pays for cache access.
    """
    unlock = db.scalar(
        select(UserCacheUnlock).where(
            UserCacheUnlock.ownerId == owner_id,
            UserCacheUnlock.targetString == target_string
        )
    )
    return unlock is not None


def grant_user_cache_unlock(
    db: Session,
    owner_id: str,
    target_string: str
) -> UserCacheUnlock:
    """
    Grant a user access to cached data without recharging.
    Used when a team member pays for cache access.
    """
    unlock = UserCacheUnlock(
        ownerId=owner_id,
        targetString=target_string,
        unlockedAt=datetime.utcnow()
    )
    db.add(unlock)
    db.flush()
    return unlock


def deduplicate_keywords_for_api_call(
    db: Session,
    keyword_requests: list[dict],
    force_refresh: bool = False
) -> tuple[list[dict], list[dict]]:
    """
    Deduplicate keyword requests and separate cached vs. missing.
    
    Args:
        keyword_requests: List of {"keyword": str, "location": str} dicts
        force_refresh: If True, ignore cache and fetch all from API
    
    Returns:
        Tuple of (missing_keywords, cached_results)
        - missing_keywords: Keywords that need API call
        - cached_results: Keywords served from cache
    """
    if force_refresh:
        return keyword_requests, []
    
    cached_results = []
    missing_keywords = []
    seen_keys = set()
    
    for req in keyword_requests:
        keyword = req.get("keyword", "").lower().strip()
        location = req.get("location", "India")
        key = (keyword, location)
        
        # Skip duplicates in the same request batch
        if key in seen_keys:
            continue
        seen_keys.add(key)
        
        # Check global cache
        cached = get_cached_keyword_metrics(db, keyword, location)
        
        if cached:
            cached_results.append(cached)
        else:
            missing_keywords.append(req)
    
    logger.info(
        f"Deduplicated {len(keyword_requests)} requests: "
        f"{len(cached_results)} from cache, {len(missing_keywords)} need API call"
    )
    
    return missing_keywords, cached_results
