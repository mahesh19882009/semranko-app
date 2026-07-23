from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ApiError
from app.db.models import Audit, AuditIssue, Project
from app.utils.serializers import model_to_dict
from app.services.notification_service import create_notification


def normalize_domain(value: str = "") -> str:
    return (
        value.strip()
        .lower()
        .removeprefix("https://")
        .removeprefix("http://")
        .removeprefix("www.")
        .rstrip("/")
    )


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


def build_audit_issues(project: Project) -> list[dict]:
    issues: list[dict] = []
    clean_domain = normalize_domain(project.domain or "")
    keywords = project.keywords or []
    competitors = project.competitors or []
    rankings = sorted(project.rankResults or [], key=lambda row: row.checkedAt, reverse=True)

    if not clean_domain:
        issues.append(
            {
                "title": "Project domain is missing",
                "description": "This project does not have a valid domain configured.",
                "category": "TECHNICAL",
                "severity": "CRITICAL",
                "recommendation": "Add a valid project domain in the project setup.",
            }
        )
    elif "." not in clean_domain:
        issues.append(
            {
                "title": "Project domain format looks incomplete",
                "description": "The saved domain does not appear to include a full hostname.",
                "category": "TECHNICAL",
                "severity": "WARNING",
                "recommendation": "Update the project domain to a valid value like example.com.",
            }
        )
    else:
        issues.append(
            {
                "title": "Project domain is configured",
                "description": f"Domain {clean_domain} is available for this project.",
                "category": "TECHNICAL",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

    if len(keywords) == 0:
        issues.append(
            {
                "title": "No keywords added",
                "description": "The project has no tracked keywords yet.",
                "category": "CONTENT",
                "severity": "CRITICAL",
                "recommendation": "Add at least 5 target keywords for meaningful tracking.",
            }
        )
    elif len(keywords) < 5:
        suffix = "" if len(keywords) == 1 else "s"
        issues.append(
            {
                "title": "Keyword coverage is low",
                "description": f"Only {len(keywords)} keyword{suffix} added to this project.",
                "category": "CONTENT",
                "severity": "WARNING",
                "recommendation": "Add more target keywords to improve audit usefulness.",
            }
        )
    else:
        issues.append(
            {
                "title": "Keyword coverage is healthy",
                "description": f"{len(keywords)} keywords are available for analysis.",
                "category": "CONTENT",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

    if len(competitors) == 0:
        issues.append(
            {
                "title": "No competitors added",
                "description": "Competitor benchmarking is not available yet.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Add at least 2 competitors for comparison insights.",
            }
        )
    elif len(competitors) < 2:
        issues.append(
            {
                "title": "Competitor set is limited",
                "description": f"Only {len(competitors)} competitor has been added.",
                "category": "ON_PAGE",
                "severity": "WARNING",
                "recommendation": "Add at least one more competitor for better benchmarking.",
            }
        )
    else:
        issues.append(
            {
                "title": "Competitor coverage is available",
                "description": f"{len(competitors)} competitors are available for comparison.",
                "category": "ON_PAGE",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

    if len(rankings) == 0:
        issues.append(
            {
                "title": "No ranking data found",
                "description": "Rank checks have not been run for this project yet.",
                "category": "PERFORMANCE",
                "severity": "CRITICAL",
                "recommendation": "Run a rank check to populate ranking performance data.",
            }
        )
    else:
        latest_checked_at = rankings[0].checkedAt if rankings else None
        top10_count = len(
            [row for row in rankings if isinstance(row.position, int) and row.position > 0 and row.position <= 10]
        )

        issues.append(
            {
                "title": "Ranking data is available",
                "description": (
                    f"Latest rank check was recorded on {latest_checked_at.strftime('%m/%d/%Y')}."
                    if latest_checked_at
                    else "Ranking data exists for this project."
                ),
                "category": "PERFORMANCE",
                "severity": "PASSED",
                "recommendation": "No action needed.",
            }
        )

        if top10_count == 0:
            issues.append(
                {
                    "title": "No top 10 rankings found",
                    "description": "Tracked keywords are not yet ranking in the top 10 positions.",
                    "category": "PERFORMANCE",
                    "severity": "WARNING",
                    "recommendation": "Improve pages targeting these keywords and rerun rank checks.",
                }
            )
        else:
            suffix = "" if top10_count == 1 else "s"
            issues.append(
                {
                    "title": "Top 10 visibility detected",
                    "description": f"{top10_count} ranking result{suffix} found in the top 10.",
                    "category": "PERFORMANCE",
                    "severity": "PASSED",
                    "recommendation": "Continue monitoring and optimize remaining keywords.",
                }
            )

    return issues


def build_audit_summary(issues: list[dict]) -> dict:
    critical_issues = len([item for item in issues if item["severity"] == "CRITICAL"])
    warning_issues = len([item for item in issues if item["severity"] == "WARNING"])
    passed_checks = len([item for item in issues if item["severity"] == "PASSED"])
    total_issues = len(issues)
    score = max(0, min(100, passed_checks * 20 - critical_issues * 15 - warning_issues * 5 + 50))

    summary = "Audit completed."
    if critical_issues > 0:
        crit_suffix = "" if critical_issues == 1 else "s"
        warn_suffix = "" if warning_issues == 1 else "s"
        summary = f"Audit found {critical_issues} critical issue{crit_suffix} and {warning_issues} warning{warn_suffix}."
    elif warning_issues > 0:
        warn_suffix = "" if warning_issues == 1 else "s"
        summary = f"Audit found {warning_issues} warning{warn_suffix} and no critical issues."
    else:
        summary = "Audit completed with no critical or warning issues."

    return {
        "score": score,
        "totalIssues": total_issues,
        "criticalIssues": critical_issues,
        "warningIssues": warning_issues,
        "passedChecks": passed_checks,
        "summary": summary,
    }


def run_project_audit(db: Session, user_id: str, project_id: str) -> dict:
    project = ensure_project_access(db, user_id, project_id)
    issues = build_audit_issues(project)
    summary = build_audit_summary(issues)

    audit = Audit(
        projectId=project_id,
        status="COMPLETED",
        score=summary["score"],
        totalIssues=summary["totalIssues"],
        criticalIssues=summary["criticalIssues"],
        warningIssues=summary["warningIssues"],
        passedChecks=summary["passedChecks"],
        summary=summary["summary"],
    )
    db.add(audit)
    db.flush()

    for issue in issues:
        db.add(AuditIssue(auditId=audit.id, **issue))

    db.commit()

    create_notification(
        db,
        user_id=user_id,
        project_id=project_id,
        type="AUDIT_COMPLETED",
        title="Audit completed",
        message=f"{project.name} audit completed successfully.",
        severity="info",
        entity_type="audit",
        entity_id=audit.id,
        metadata={
            "auditId": audit.id,
            "projectId": project_id,
            "score": audit.score,
            "criticalIssues": audit.criticalIssues,
            "warningIssues": audit.warningIssues,
        },
    )

    db.commit()

    return get_audit_by_id(db, audit.id)


def get_audit_by_id(db: Session, audit_id: str) -> dict:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id).options(selectinload(Audit.issues)))
    if not audit:
        raise ApiError(404, "Audit not found")

    data = model_to_dict(audit)
    issues = [model_to_dict(issue) for issue in audit.issues]
    issues.sort(key=lambda item: (item["severity"], item["createdAt"]), reverse=False)
    data["issues"] = issues
    return data


def get_project_audits(db: Session, user_id: str, project_id: str) -> list[dict]:
    ensure_project_access(db, user_id, project_id)

    audits = db.scalars(
        select(Audit)
        .where(Audit.projectId == project_id)
        .order_by(desc(Audit.createdAt))
        .options(selectinload(Audit.issues))
    ).all()

    result = []
    for audit in audits:
        item = model_to_dict(audit)
        issues = [model_to_dict(issue) for issue in audit.issues]
        issues.sort(key=lambda row: (row["severity"], row["createdAt"]))
        item["issues"] = issues
        result.append(item)

    return result
