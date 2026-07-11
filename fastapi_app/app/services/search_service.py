from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Keyword, Project, Report


def search_global(db: Session, user_id: str, query: str, project_id: Optional[str] = None) -> dict:
    q = (query or "").strip()
    if not q:
        raise ApiError(400, "Search query is required")

    scoped_project = None
    if project_id:
        scoped_project = db.scalar(
            select(Project).where(Project.id == project_id, Project.userId == user_id)
        )
        if not scoped_project:
            raise ApiError(404, "Project not found")

    project_filters = [Project.userId == user_id]
    if project_id:
        project_filters.append(Project.id == project_id)

    project_rows = db.execute(
        select(Project)
        .where(
            Project.userId == user_id,
            or_(
                Project.name.ilike(f"%{q}%"),
                Project.domain.ilike(f"%{q}%"),
            ),
        )
        .order_by(Project.createdAt.desc())
        .limit(8)
    ).scalars().all()

    keyword_rows = db.execute(
        select(Keyword, Project)
        .join(Project, Project.id == Keyword.projectId)
        .where(
            *project_filters,
            or_(
                Keyword.keyword.ilike(f"%{q}%"),
                Keyword.location.ilike(f"%{q}%"),
                Keyword.device.ilike(f"%{q}%"),
                Project.name.ilike(f"%{q}%"),
                Project.domain.ilike(f"%{q}%"),
            ),
        )
        .order_by(Keyword.createdAt.desc())
        .limit(8)
    ).all()

    report_rows = db.execute(
        select(Report, Project)
        .join(Project, Project.id == Report.projectId)
        .where(
            *project_filters,
            or_(
                Report.title.ilike(f"%{q}%"),
                Report.summary.ilike(f"%{q}%"),
                Report.period.ilike(f"%{q}%"),
                Project.name.ilike(f"%{q}%"),
                Project.domain.ilike(f"%{q}%"),
            ),
        )
        .order_by(Report.createdAt.desc())
        .limit(8)
    ).all()

    projects = [
        {
            "id": project.id,
            "name": project.name,
            "domain": project.domain,
            "createdAt": project.createdAt.isoformat() if project.createdAt else None,
        }
        for project in project_rows
    ]

    keywords = [
        {
            "id": keyword.id,
            "keyword": keyword.keyword,
            "location": getattr(keyword, "location", None),
            "device": getattr(keyword, "device", None),
            "createdAt": keyword.createdAt.isoformat() if keyword.createdAt else None,
            "project": {
                "id": project.id,
                "name": project.name,
                "domain": project.domain,
            },
        }
        for keyword, project in keyword_rows
    ]

    reports = [
        {
            "id": report.id,
            "title": report.title,
            "summary": getattr(report, "summary", None),
            "period": getattr(report, "period", None),
            "status": getattr(report, "status", None),
            "createdAt": report.createdAt.isoformat() if report.createdAt else None,
            "project": {
                "id": project.id,
                "name": project.name,
                "domain": project.domain,
            },
        }
        for report, project in report_rows
    ]

    return {
        "query": q,
        "projectId": project_id,
        "projects": projects,
        "keywords": keywords,
        "reports": reports,
        "totals": {
            "projects": len(projects),
            "keywords": len(keywords),
            "reports": len(reports),
        },
    }