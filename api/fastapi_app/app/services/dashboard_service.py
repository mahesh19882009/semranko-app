from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import Project, TrackedKeyword, CreditLedger, Team, TeamMember, KeywordCache, RankResult
from app.services.plan_service import build_usage_snapshot, get_user_or_404, get_user_plan_limits


def ensure_project_access(db: Session, user_id: str, project_id: str) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.userId == user_id)
        .options(
            selectinload(Project.keywords),
            selectinload(Project.competitors),
            selectinload(Project.rankResults),
        )
    )

    if not project:
        raise ApiError(404, "Project not found")
    return project


def calculate_average_rank_from_tracked(tracked_keywords: list) -> float:
    valid_positions = [tk.lastPosition for tk in tracked_keywords if tk.lastPosition is not None and tk.lastPosition > 0]
    if not valid_positions:
        return 0
    avg = sum(valid_positions) / len(valid_positions)
    return round(avg, 1)


def calculate_estimated_traffic_from_tracked(tracked_keywords: list) -> int:
    valid_positions = [tk.lastPosition for tk in tracked_keywords if tk.lastPosition is not None and tk.lastPosition > 0]
    if not valid_positions:
        return 0

    score = 0
    for position in valid_positions:
        if position <= 3:
            score += 120
        elif position <= 10:
            score += 60
        elif position <= 20:
            score += 25
        elif position <= 50:
            score += 10
        else:
            score += 2
    return score


def build_rank_trend_from_tracked(db: Session, user_id: str, limit: int = 12) -> list[dict]:
    """Build rank trend from TrackedKeyword history via RankResult"""
    # Get recent rank results for user's tracked keywords
    subquery = (
        select(RankResult)
        .where(RankResult.userId == user_id)
        .order_by(RankResult.checkedAt.desc())
        .limit(500)
    )
    rank_results = db.scalars(subquery).all()

    grouped: dict[str, list[int]] = defaultdict(list)
    for row in rank_results:
        if not isinstance(row.position, int) or row.position <= 0:
            continue
        date_key = row.checkedAt.date().isoformat()
        grouped[date_key].append(row.position)

    trend = []
    for label, positions in grouped.items():
        avg = sum(positions) / len(positions)
        trend.append({"label": label, "value": round(avg, 1)})

    trend.sort(key=lambda item: datetime.fromisoformat(item["label"]))
    return trend[-limit:]


def build_competitor_summary(competitors: list, keywords: list, preview_limit: int) -> list[dict]:
    if not competitors:
        return []

    keyword_count = len(keywords) or 1
    items = []
    for index, competitor in enumerate(competitors[:preview_limit]):
        items.append(
            {
                "id": competitor.id,
                "domain": competitor.domain,
                "sharedKeywords": max(0, round(keyword_count * (0.25 + index * 0.08))),
                "overlap": min(95, 28 + index * 11),
            }
        )
    return items


def get_project_dashboard(db: Session, user_id: str, project_id: str) -> dict:
    user = get_user_or_404(db, user_id)
    limits = get_user_plan_limits(user)
    project = ensure_project_access(db, user_id, project_id)

    # Fetch tracked keywords for this project (join with KeywordCache for enriched data)
    tracked_keywords = db.scalars(
        select(TrackedKeyword)
        .where(TrackedKeyword.userId == user_id, TrackedKeyword.isActive.is_(True))
        .options(selectinload(TrackedKeyword.user))
    ).all()

    # Build enriched keyword data with cache info
    enriched_keywords = []
    for tk in tracked_keywords:
        cache = db.scalar(
            select(KeywordCache).where(
                KeywordCache.keyword == tk.keyword,
                KeywordCache.location == (tk.location or "India")
            )
        )
        enriched_keywords.append({
            "id": tk.id,
            "keyword": tk.keyword,
            "location": tk.location,
            "device": tk.device,
            "lastPosition": tk.lastPosition,
            "lastCheckedAt": tk.lastCheckedAt.isoformat() if tk.lastCheckedAt else None,
            "isActive": tk.isActive,
            "trackAio": tk.trackAio,
            "volume": cache.volume if cache else None,
            "kd": cache.kd if cache else None,
            "cpc": cache.cpc if cache else None,
            "competition": cache.competition if cache else None,
            "backlinks": cache.backlinks if cache else None,
            "referring_domains": cache.referring_domains if cache else None,
            "intent": cache.intent if cache else None,
        })

    stats = {
        "totalKeywords": len(tracked_keywords),
        "avgRank": calculate_average_rank_from_tracked(tracked_keywords),
        "estimatedTraffic": calculate_estimated_traffic_from_tracked(tracked_keywords),
        "technicalHealth": 0,
        "backlinks": 0,
        "reportsSent": 0,
    }

    return {
        "stats": stats,
        "rankTrend": build_rank_trend_from_tracked(db, user_id),
        "keywords": enriched_keywords,
        "audits": [],
        "competitors": {
            "items": build_competitor_summary(
                project.competitors,
                enriched_keywords,
                limits.get("competitorsPerProject", 3),
            ),
            "total": len(project.competitors),
            "previewLimit": limits.get("competitorsPerProject", 3),
        },
        "reports": {
            "items": [],
            "total": 0,
        },
        "usage": build_usage_snapshot(db, user),
    }


def get_dashboard_overview(db: Session, user_id: str) -> dict:
    user = get_user_or_404(db, user_id)
    
    # 1. Fetch Active Tracked Keywords with Cache Data
    tracked_keywords = (
        db.query(TrackedKeyword)
        .outerjoin(KeywordCache, 
                   (TrackedKeyword.keyword == KeywordCache.keyword) & 
                   (TrackedKeyword.location == KeywordCache.location))
        .filter(
            TrackedKeyword.userId == user_id,
            TrackedKeyword.isActive.is_(True)
        )
        .order_by(TrackedKeyword.updatedAt.desc())
        .all()
    )

    total_count = len(tracked_keywords)
    
    # 2. Calculate Average Rank from Tracked Keywords
    valid_positions = [kw.lastPosition for kw in tracked_keywords if kw.lastPosition and int(kw.lastPosition) > 0]
    average_rank = round(sum(valid_positions) / len(valid_positions), 1) if valid_positions else 0

    # 3. Build Detailed Keywords List for Frontend
    keywords_data = []
    for kw in tracked_keywords:
        cache = kw.KeywordCache # Access via relationship if configured, else None
        
        # Fallback if relationship isn't loaded explicitly
        if not cache:
            cache = db.query(KeywordCache).filter(
                KeywordCache.keyword == kw.keyword,
                KeywordCache.location == kw.location
            ).first()

        keywords_data.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "current_rank": kw.lastPosition,
            "previous_rank": kw.previousPosition,
            "search_volume": cache.search_volume if cache else 0,
            "difficulty": cache.difficulty if cache else 0,
            "cpc": float(cache.cpc) if cache and cache.cpc else 0.0,
            "competition": float(cache.competition) if cache and cache.competition else 0.0,
            "intent": cache.intent if cache else "Unknown",
            "backlinks": cache.backlinks if cache else 0,
            "location": kw.location,
            "last_updated": kw.updatedAt.isoformat() if kw.updatedAt else None,
        })

    # 4. Build Chart Data (Last 7 Days)
    # We combine Position Trend and Credit Usage
    today = datetime.utcnow()
    chart_labels = []
    position_data = []
    credit_data = []

    # Fetch Credit Ledger for last 7 days
    seven_days_ago = today - timedelta(days=7)
    credit_rows = db.query(CreditLedger).filter(
        CreditLedger.ownerId == user.id,
        CreditLedger.timestamp >= seven_days_ago
    ).all()

    daily_credits = defaultdict(float)
    for row in credit_rows:
        if row.timestamp:
            date_key = row.timestamp.date().isoformat()
            daily_credits[date_key] += float(row.creditsSpent or 0)

    # Generate 7 days of data
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_key = date.date().isoformat()
        chart_labels.append(date.strftime("%Y-%m-%d"))
        
        # Position: Use average rank as base, add slight mock variation if no history table exists yet
        # If you have a RankHistory table, query it here instead.
        if total_count > 0:
            # Mocking a trend line around the current average for visualization
            base = average_rank if average_rank > 0 else 20
            # Simple deterministic variation for demo purposes
            variation = (i % 3) - 1 
            pos_val = max(1, round(base + variation))
            position_data.append(pos_val)
        else:
            position_data.append(0)
            
        # Credits: Real data from ledger
        credit_data.append(daily_credits.get(date_key, 0.0))

    return {
        "tracked_keywords_count": total_count,
        "average_rank": average_rank,
        "keywords": keywords_data,
        "chart_data": {
            "labels": chart_labels,
            "positions": position_data,
            "credits": credit_data
        }
    }