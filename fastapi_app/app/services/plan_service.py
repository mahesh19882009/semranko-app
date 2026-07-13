from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import Competitor, Keyword, Project, Report, User

PLAN_LIMITS = {
    "starter": {
        "projects": 1,
        "keywords": 25,
        "competitorsPerProject": 3,
        "reportsPerMonth": 2,
        "dashboardCompetitorsPreview": 3,
    },
    "pro": {
        "projects": 3,
        "keywords": 100,
        "competitorsPerProject": 10,
        "reportsPerMonth": 10,
        "dashboardCompetitorsPreview": 5,
    },
    "agency": {
        "projects": 10,
        "keywords": 300,
        "competitorsPerProject": 25,
        "reportsPerMonth": 25,
        "dashboardCompetitorsPreview": 10,
    },
}


def get_user_or_404(db: Session, user_id: str) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")
    return user


def get_plan_key(user: User) -> str:
    return (getattr(user, "selectedPlan", None) or "starter").strip().lower()


def get_user_plan_limits(user: User) -> dict:
    plan_key = get_plan_key(user)
    return PLAN_LIMITS.get(plan_key, PLAN_LIMITS["starter"])


def ensure_subscription_active(user: User) -> None:
    status = (getattr(user, "subscriptionStatus", None) or "trialing").strip().lower()

    if status not in {"trialing", "active"}:
        raise ApiError(403, "Your subscription is inactive. Please upgrade to continue.")

    trial_ends_at = getattr(user, "trialEndsAt", None)
    if status == "trialing" and trial_ends_at and trial_ends_at < datetime.utcnow():
        raise ApiError(403, "Your trial has expired. Please upgrade to continue.")


def count_user_projects(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Project).where(Project.userId == user_id)
    ) or 0


def count_user_keywords(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Keyword)
        .join(Project, Project.id == Keyword.projectId)
        .where(Project.userId == user_id)
    ) or 0


def count_project_competitors(db: Session, project_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Competitor).where(Competitor.projectId == project_id)
    ) or 0


def count_user_reports_this_month(db: Session, user_id: str) -> int:
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    return db.scalar(
        select(func.count())
        .select_from(Report)
        .join(Project, Project.id == Report.projectId)
        .where(Project.userId == user_id, Report.createdAt >= month_start)
    ) or 0


def build_usage_snapshot(db: Session, user: User) -> dict:
    limits = get_user_plan_limits(user)

    return {
        "plan": get_plan_key(user),
        "subscriptionStatus": user.subscriptionStatus,
        "trialEndsAt": user.trialEndsAt.isoformat() if user.trialEndsAt else None,
        "usage": {
            "projects": count_user_projects(db, user.id),
            "keywords": count_user_keywords(db, user.id),
            "reportsThisMonth": count_user_reports_this_month(db, user.id),
        },
        "limits": {
            "projects": limits["projects"],
            "keywords": limits["keywords"],
            "competitorsPerProject": limits["competitorsPerProject"],
            "reportsPerMonth": limits["reportsPerMonth"],
        },
    }


def ensure_project_limit(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)

    used = count_user_projects(db, user_id)
    allowed = limits["projects"]

    if used >= allowed:
        raise ApiError(403, f"Project limit reached. Your current plan allows {allowed} project(s).")


def ensure_keyword_limit(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)

    used = count_user_keywords(db, user_id)
    allowed = limits["keywords"]

    if used >= allowed:
        raise ApiError(403, f"Keyword limit reached. Your current plan allows {allowed} tracked keyword(s).")


def ensure_competitor_limit(db: Session, user_id: str, project_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)

    used = count_project_competitors(db, project_id)
    allowed = limits["competitorsPerProject"]

    if used >= allowed:
        raise ApiError(403, f"Competitor limit reached. Your current plan allows {allowed} competitor(s) per project.")


def ensure_report_limit(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)

    used = count_user_reports_this_month(db, user_id)
    allowed = limits["reportsPerMonth"]

    if used >= allowed:
        raise ApiError(403, f"Monthly report limit reached. Your current plan allows {allowed} report(s) per month.")