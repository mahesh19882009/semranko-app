from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import Project, TrackedKeyword, CreditLedger, Team, TeamMember
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


def calculate_average_rank(rank_results: list) -> float:
    valid_positions = [row.position for row in rank_results if isinstance(row.position, int) and row.position > 0]
    if not valid_positions:
        return 0
    avg = sum(valid_positions) / len(valid_positions)
    return round(avg, 1)


def calculate_estimated_traffic(rank_results: list) -> int:
    valid_positions = [row.position for row in rank_results if isinstance(row.position, int) and row.position > 0]
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


def build_rank_trend(rank_results: list) -> list[dict]:
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
    return trend[-12:]


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

    rank_results = sorted(project.rankResults, key=lambda r: r.checkedAt, reverse=True)[:500]

    stats = {
        "totalKeywords": len(project.keywords),
        "avgRank": calculate_average_rank(rank_results),
        "estimatedTraffic": calculate_estimated_traffic(rank_results),
        "technicalHealth": 0,
        "backlinks": 0,
        "reportsSent": 0,
    }

    return {
        "stats": stats,
        "rankTrend": build_rank_trend(rank_results),
        "audits": [],
        "competitors": {
            "items": build_competitor_summary(
                project.competitors,
                project.keywords,
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
    owner_id = get_user_or_404(db, user_id).id

    tracked_keywords_count = db.scalar(
        select(func.count())
        .select_from(TrackedKeyword)
        .where(
            TrackedKeyword.userId == user_id,
            TrackedKeyword.isActive.is_(True),
        )
    ) or 0

    rank_rows = db.scalars(
        select(TrackedKeyword.lastPosition).where(
            TrackedKeyword.userId == user_id,
            TrackedKeyword.isActive.is_(True),
            TrackedKeyword.lastPosition.is_not(None),
        )
    ).all()

    valid_positions = [int(pos) for pos in rank_rows if pos and int(pos) > 0]
    average_rank = round(sum(valid_positions) / len(valid_positions), 1) if valid_positions else 0

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    credit_rows = db.scalars(
        select(CreditLedger)
        .where(
            CreditLedger.ownerId == owner_id,
            CreditLedger.timestamp >= thirty_days_ago,
            CreditLedger.creditsSpent.is_not(None),
        )
        .order_by(CreditLedger.timestamp.asc())
    ).all()

    daily_spend: dict[str, float] = defaultdict(float)
    for row in credit_rows:
        if row.timestamp:
            date_key = row.timestamp.date().isoformat()
            daily_spend[date_key] += float(row.creditsSpent or 0)

    chart_data = [
        {"label": date_key, "value": round(total, 2)}
        for date_key, total in sorted(daily_spend.items())
    ]

    return {
        "tracked_keywords_count": tracked_keywords_count,
        "average_rank": average_rank,
        "chart_data": chart_data,
    }