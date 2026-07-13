from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import Audit, Project
from app.services.plan_service import build_usage_snapshot, get_user_or_404, get_user_plan_limits


def ensure_project_access(db: Session, user_id: str, project_id: str) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id, Project.userId == user_id)
        .options(
            selectinload(Project.keywords),
            selectinload(Project.competitors),
            selectinload(Project.reports),
            selectinload(Project.audits).selectinload(Audit.issues),
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


def build_audit_summary(latest_audit) -> list[dict]:
    if not latest_audit:
        return [
            {"label": "Issues found", "value": 0},
            {"label": "Warnings", "value": 0},
            {"label": "Passed checks", "value": 0},
        ]

    return [
        {"label": "Issues found", "value": latest_audit.criticalIssues or 0},
        {"label": "Warnings", "value": latest_audit.warningIssues or 0},
        {"label": "Passed checks", "value": latest_audit.passedChecks or 0},
    ]


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


def build_reports_summary(reports: list) -> list[dict]:
    items = []
    for report in reports[:5]:
        items.append(
            {
                "id": report.id,
                "name": report.title,
                "schedule": report.period,
                "type": "SEO Report",
                "status": "Active" if report.status == "COMPLETED" else report.status,
            }
        )
    return items


def get_project_dashboard(db: Session, user_id: str, project_id: str) -> dict:
    user = get_user_or_404(db, user_id)
    limits = get_user_plan_limits(user)
    project = ensure_project_access(db, user_id, project_id)

    audits = sorted(project.audits, key=lambda a: a.createdAt, reverse=True)
    reports = sorted(project.reports, key=lambda r: r.createdAt, reverse=True)
    rank_results = sorted(project.rankResults, key=lambda r: r.checkedAt, reverse=True)[:500]

    latest_audit = audits[0] if audits else None

    stats = {
        "totalKeywords": len(project.keywords),
        "avgRank": calculate_average_rank(rank_results),
        "estimatedTraffic": calculate_estimated_traffic(rank_results),
        "technicalHealth": getattr(latest_audit, "score", 0) or 0,
        "backlinks": 0,
        "reportsSent": len(reports),
    }

    return {
        "stats": stats,
        "rankTrend": build_rank_trend(rank_results),
        "audits": build_audit_summary(latest_audit),
        "competitors": {
            "items": build_competitor_summary(
                project.competitors,
                project.keywords,
                limits["dashboardCompetitorsPreview"],
            ),
            "total": len(project.competitors),
            "previewLimit": limits["dashboardCompetitorsPreview"],
        },
        "reports": {
            "items": build_reports_summary(reports),
            "total": len(reports),
        },
        "usage": build_usage_snapshot(db, user),
    }