from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session, selectinload, joinedload

from app.core.errors import ApiError
from app.db.models import Project, Report
from app.services.notification_service import create_notification
from app.services.plan_service import ensure_report_limit
from app.utils.serializers import model_to_dict


def ensure_project_access(db: Session, user_id: str, project_id: str, include_relations: bool = False) -> Project:
    query = select(Project).where(Project.id == project_id, Project.userId == user_id)
    if include_relations:
        query = query.options(
            selectinload(Project.keywords),
            selectinload(Project.competitors),
            selectinload(Project.rankResults),
        )

    project = db.scalar(query)
    if not project:
        raise ApiError(404, "Project not found")
    return project


def build_report_summary(project: Project) -> dict:
    keyword_count = len(project.keywords or [])
    competitor_count = len(project.competitors or [])
    rankings = sorted(project.rankResults or [], key=lambda row: row.checkedAt, reverse=True)

    unique_keyword_map: dict[str, object] = {}
    for row in rankings:
        key = row.keywordId or row.keywordText
        if not key:
            continue
        if key not in unique_keyword_map:
            unique_keyword_map[key] = row

    latest_rankings = list(unique_keyword_map.values())
    top10_count = len(
        [
            item
            for item in latest_rankings
            if isinstance(item.position, int) and item.position > 0 and item.position <= 10
        ]
    )

    visibility_score = max(0, min(100, 50 + top10_count * 10 - max(0, keyword_count - top10_count) * 2))

    summary = "Report generated successfully."
    if not latest_rankings:
        summary = "No ranking data found yet. Run rank tracking to generate deeper report insights."
    elif top10_count == 0:
        summary = "Ranking data exists, but no tracked keywords are currently in the top 10."
    else:
        suffix = "" if top10_count == 1 else "s"
        summary = f"{top10_count} tracked keyword{suffix} currently rank in the top 10."

    return {
        "visibilityScore": visibility_score,
        "keywordCount": keyword_count,
        "top10Count": top10_count,
        "competitorCount": competitor_count,
        "summary": summary,
    }


def create_project_report(db: Session, user_id: str, project_id: str) -> dict:
    ensure_report_limit(db, user_id)
    project = ensure_project_access(db, user_id, project_id, include_relations=True)
    computed = build_report_summary(project)

    # Calculate score from visibility score
    score = computed["visibilityScore"]
    
    # Generate strengths and recommendations based on data
    strengths = []
    recommendations = []
    
    if computed["top10Count"] > 0:
        strengths.append(f"{computed['top10Count']} keywords ranking in top 10")
    if computed["keywordCount"] > 0:
        strengths.append(f"Tracking {computed['keywordCount']} keywords")
    if computed["competitorCount"] > 0:
        strengths.append(f"Monitoring {computed['competitorCount']} competitors")
    
    if computed["top10Count"] < computed["keywordCount"] / 2:
        recommendations.append("Focus on improving keyword rankings to increase visibility")
    if computed["keywordCount"] < 10:
        recommendations.append("Add more keywords to track for better insights")
    if computed["competitorCount"] == 0:
        recommendations.append("Add competitors to monitor their performance")

    report = Report(
        projectId=project_id,
        title=f"{project.name} SEO Report",
        period="LAST_30_DAYS",
        status="COMPLETED",
        summary=computed["summary"],
        visibilityScore=computed["visibilityScore"],
        keywordCount=computed["keywordCount"],
        top10Count=computed["top10Count"],
        competitorCount=computed["competitorCount"],
    )

    db.add(report)
    db.flush()

    create_notification(
        db,
        user_id=user_id,
        project_id=project_id,
        type="REPORT_READY",
        title="Report generated",
        message=f"{project.name} report was generated successfully.",
        severity="info",
        entity_type="report",
        entity_id=report.id,
        metadata={
            "reportId": report.id,
            "projectId": project_id,
            "projectName": project.name,
            "reportTitle": report.title,
            "period": report.period,
            "event": "REPORT_READY",
        },
    )

    db.commit()
    db.refresh(report)

    return model_to_dict(report)


def get_project_reports(db: Session, user_id: str, project_id: str) -> list[dict]:
    ensure_project_access(db, user_id, project_id)

    reports = db.scalars(
        select(Report).where(Report.projectId == project_id).order_by(desc(Report.createdAt))
    ).all()
    return [model_to_dict(report) for report in reports]


def get_single_report(db: Session, user_id: str, report_id: str) -> dict:
    report = db.scalar(
        select(Report)
        .join(Project, Project.id == Report.projectId)
        .where(Report.id == report_id, Project.userId == user_id)
        .options(selectinload(Report.project))
    )

    if not report:
        raise ApiError(404, "Report not found")

    data = model_to_dict(report)
    if report.project:
        data["project"] = {
            "id": report.project.id,
            "name": report.project.name,
            "domain": report.project.domain,
        }
    return data


def delete_single_report(db: Session, user_id: str, report_id: str) -> dict:
    report = db.scalar(
        select(Report)
        .options(joinedload(Report.project))
        .join(Project, Project.id == Report.projectId)
        .where(Report.id == report_id, Project.userId == user_id)
    )

    if not report:
        raise ApiError(404, "Report not found")

    deleted = model_to_dict(report)
    project_id = report.projectId
    project_name = report.project.name if report.project else None
    report_title = report.title
    period = report.period
    report_entity_id = report.id
    create_notification(
        db,
        user_id=user_id,
        project_id=project_id,
        type="REPORT_DELETED",
        title="Report deleted",
        message=f"{report_title} was deleted successfully.",
        severity="info",
        entity_type="report",
        entity_id=report_entity_id,
        metadata={
            "reportId": report_entity_id,
            "projectId": project_id,
            "projectName": project_name,
            "reportTitle": report_title,
            "period": period,
            "event": "REPORT_DELETED",
        },
    )
    db.execute(delete(Report).where(Report.id == report_id))
    db.commit()
    return deleted


def delete_all_project_reports(db: Session, user_id: str, project_id: str) -> dict:
    ensure_project_access(db, user_id, project_id)

    reports = db.scalars(
        select(Report)
        .options(joinedload(Report.project))
        .join(Project, Project.id == Report.projectId)
        .where(Report.projectId == project_id, Project.userId == user_id)
    ).all()

    if not reports:
        raise ApiError(404, "Report not found")

    deleted_count = len(reports)
    project_name = reports[0].project.name if reports[0].project else None
    deleted_report_ids = [report.id for report in reports]
    deleted_report_titles = [report.title for report in reports]

    create_notification(
        db,
        user_id=user_id,
        project_id=project_id,
        type="REPORTS_DELETED",
        title="Reports deleted",
        message=f"{deleted_count} reports were deleted successfully.",
        severity="info",
        entity_type="report",
        entity_id=None,
        metadata={
            "projectId": project_id,
            "projectName": project_name,
            "deletedCount": deleted_count,
            "reportIds": deleted_report_ids,
            "reportTitles": deleted_report_titles,
            "event": "REPORTS_DELETED",
        },
    )

    db.execute(delete(Report).where(Report.projectId == project_id))
    db.commit()

    return {"projectId": project_id, "deletedCount": deleted_count}
    