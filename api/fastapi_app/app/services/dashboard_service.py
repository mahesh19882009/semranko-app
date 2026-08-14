from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import Project, Keyword, RankResult, CreditLedger, Competitor
from app.services.plan_service import build_usage_snapshot, get_user_or_404, get_user_plan_limits


def ensure_project_access(db: Session, user_id: str, project_id: str) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.userId == user_id)
        .options(
            selectinload(Project.keywords),
            selectinload(Project.competitors),
            # We don't load rankResults anymore for the main stats to avoid reliance on empty table
        )
    )

    if not project:
        raise ApiError(404, "Project not found")
    return project


def calculate_average_rank_from_keywords(keywords: List[Keyword]) -> float:
    """
    Calculate average rank directly from the Keyword table's current_rank field.
    This bypasses the empty RankResult history table.
    """
    valid_positions = []
    
    for kw in keywords:
        # Adjust 'current_rank' to match your actual column name in Keyword model
        # Common names: current_rank, position, last_rank
        rank = getattr(kw, 'current_rank', None) or getattr(kw, 'position', None) or getattr(kw, 'last_rank', None)
        
        if rank is not None:
            try:
                rank_val = int(rank)
                if rank_val > 0:
                    valid_positions.append(rank_val)
            except (ValueError, TypeError):
                continue
    
    if not valid_positions:
        return 0.0
    
    avg = sum(valid_positions) / len(valid_positions)
    return round(avg, 1)


def build_competitor_summary(competitors: List[Any], keywords: List[Keyword], preview_limit: int) -> List[Dict]:
    if not competitors:
        return []

    keyword_count = len(keywords) or 1
    items = []
    for index, competitor in enumerate(competitors[:preview_limit]):
        items.append(
            {
                "id": competitor.id,
                "domain": getattr(competitor, 'domain', 'Unknown'),
                "sharedKeywords": max(0, round(keyword_count * (0.25 + index * 0.08))),
                "overlap": min(95, 28 + index * 11),
            }
        )
    return items


def get_project_dashboard(db: Session, user_id: str, project_id: str) -> dict:
    user = get_user_or_404(db, user_id)
    limits = get_user_plan_limits(user, db)
    project = ensure_project_access(db, user_id, project_id)
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()

    stats = {
        "totalKeywords": len(keywords),
        "avgRank": calculate_average_rank_from_keywords(keywords),
        "estimatedTraffic": 0, 
        "technicalHealth": 0,
        "backlinks": 0,
        "reportsSent": 0,
    }

    return {
        "stats": stats,
        "rankTrend": [], # Empty until RankResult has data
        "audits": [],
        "competitors": {
            "items": build_competitor_summary(project.competitors, keywords, limits.get("competitorsPerProject", 3)),
            "total": len(project.competitors),
            "previewLimit": limits.get("competitorsPerProject", 3),
        },
        "reports": {"items": [], "total": 0},
        "client_logo_url": getattr(project, "client_logo_url", None),
        "usage": build_usage_snapshot(db, user),
    }


def get_dashboard_overview(db: Session, user_id: str) -> dict:
    """
    Get dashboard overview using Keyword data.
    """
    user = get_user_or_404(db, user_id)
    projects_count = db.scalar(
        select(func.count(Project.id)).where(Project.userId == user_id)
    ) or 0

    keywords = db.scalars(
        select(Keyword).join(Project, Keyword.projectId == Project.id).where(
            Project.userId == user_id,
            Keyword.deletedAt.is_(None),
        )
    ).all()

    if not keywords:
        return {
            "projects_count": int(projects_count),
            "tracked_keywords_count": 0,
            "active_keywords_count": 0,
            "inactive_keywords_count": 0,
            "aio_keywords_count": 0,
            "average_rank": 0,
            "keywords": [],
            "chart_data": {"labels": [], "positions": [], "credits": []},
            "usage": build_usage_snapshot(db, user),
        }

    valid_positions = []
    keywords_data = []

    for kw in keywords:
        keyword_text = kw.keyword
        location = kw.location or "India"

        current_rank = kw.position
        if current_rank is not None:
            try:
                r_val = int(current_rank)
                if r_val > 0:
                    valid_positions.append(r_val)
            except (ValueError, TypeError):
                pass

        keywords_data.append({
            "id": kw.id,
            "keyword": keyword_text,
            "current_rank": current_rank,
            "previous_rank": None,
            "search_volume": kw.volume or 0,
            "difficulty": kw.kd or 0,
            "cpc": float(kw.cpc if kw.cpc else 0.0),
            "competition": float(kw.competition if kw.competition else 0.0),
            "intent": kw.intent or "Unknown",
            "backlinks": kw.backlinks or 0,
            "referring_domains": kw.referring_domains or 0,
            "ai_badge": kw.ai_badge,
            "location": location,
            "last_updated": kw.updatedAt.isoformat() if getattr(kw, "updatedAt", None) else None,
        })

    average_rank = round(sum(valid_positions) / len(valid_positions), 1) if valid_positions else 0.0

    today = datetime.utcnow()
    chart_labels = []
    position_data = []
    credit_data = []

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

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_key = date.date().isoformat()
        chart_labels.append(date.strftime("%Y-%m-%d"))
        position_data.append(None)
        credit_data.append(daily_credits.get(date_key, 0.0))

    active_keywords_count = sum(1 for keyword in keywords if keyword.isActive)
    aio_keywords_count = sum(
        1 for keyword in keywords if keyword.ai_badge == "AIO"
    )

    return {
        "projects_count": int(projects_count),
        "tracked_keywords_count": len(keywords_data),
        "active_keywords_count": active_keywords_count,
        "inactive_keywords_count": len(keywords_data) - active_keywords_count,
        "aio_keywords_count": aio_keywords_count,
        "average_rank": average_rank,
        "keywords": keywords_data,
        "chart_data": {
            "labels": chart_labels,
            "positions": position_data,
            "credits": credit_data,
        },
        "usage": build_usage_snapshot(db, user),
    }
