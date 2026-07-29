from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import GST_RATE, get_settings
from app.services.notification_service import create_notification
from app.core.errors import ApiError
from app.db.models import Competitor, Keyword, Project, Report, Subscription, User

PLAN_DEFINITIONS = {
    "starter": {
        "key": "starter",
        "name": "Starter",
        "monthlyPrice": 1999,
        "yearlyPrice": 1499,
        "description": "Best for freelancers and small websites starting SEO tracking.",
        "highlighted": False,
        "cta": "Start Starter Trial",
        "limits": {
            "projects": 1,
            "keywords": 25,
            "competitorsPerProject": 3,
            "reportsPerMonth": 2,
            "teamMembers": 1,
            "dashboardCompetitorsPreview": 3,
        },
    },
    "pro": {
        "key": "pro",
        "name": "Pro",
        "monthlyPrice": 4999,
        "yearlyPrice": 3999,
        "description": "Ideal for growing businesses that need stronger reporting and tracking.",
        "highlighted": True,
        "cta": "Start Pro Trial",
        "limits": {
            "projects": 3,
            "keywords": 100,
            "competitorsPerProject": 10,
            "reportsPerMonth": 10,
            "teamMembers": 2,
            "dashboardCompetitorsPreview": 5,
        },
    },
    "agency": {
        "key": "agency",
        "name": "Agency",
        "monthlyPrice": 9999,
        "yearlyPrice": 7999,
        "description": "Built for agencies handling multiple clients and white-label style delivery.",
        "highlighted": False,
        "cta": "Start Agency Trial",
        "limits": {
            "projects": 10,
            "keywords": 300,
            "competitorsPerProject": 25,
            "reportsPerMonth": 25,
            "teamMembers": 5,
            "dashboardCompetitorsPreview": 10,
        },
    },
}

PLAN_ORDER = {
    "starter": 1,
    "pro": 2,
    "agency": 3,
}

TRIAL_PLAN_KEY = "starter"


def list_available_plans() -> list[dict]:
    return [
        {
            "key": plan["key"],
            "name": plan["name"],
            "monthlyPrice": plan["monthlyPrice"],
            "yearlyPrice": plan["yearlyPrice"],
            "description": plan["description"],
            "highlighted": plan["highlighted"],
            "cta": plan["cta"],
            "limits": plan["limits"],
        }
        for plan in PLAN_DEFINITIONS.values()
    ]


def get_trial_days() -> int:
    return get_settings().TRIAL_DAYS


def get_user_or_404(db: Session, user_id: str) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")
    return user


def get_subscription_status(user: User) -> str:
    raw_status = (getattr(user, "subscriptionStatus", None) or "").strip().lower()

    trial_ends_at = getattr(user, "trialEndsAt", None)
    now = datetime.utcnow()

    if trial_ends_at and trial_ends_at >= now and raw_status in {"", "trialing"}:
        return "trialing"

    if raw_status:
        return raw_status

    return "trialing"


def get_plan_key(user: User) -> str:
    return (getattr(user, "selectedPlan", None) or "starter").strip().lower()


def get_effective_plan_key(user: User) -> str:
    status = get_subscription_status(user)
    if status == "trialing":
        return TRIAL_PLAN_KEY
    selected = get_plan_key(user)
    return selected if selected in PLAN_DEFINITIONS else TRIAL_PLAN_KEY


def get_user_plan_limits(user: User) -> dict:
    effective_plan_key = get_effective_plan_key(user)
    plan = PLAN_DEFINITIONS.get(effective_plan_key, PLAN_DEFINITIONS[TRIAL_PLAN_KEY])
    return plan["limits"]


def ensure_subscription_active(user: User) -> None:
    status = get_subscription_status(user)
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


def get_user_projects(db: Session, user_id: str) -> list[Project]:
    return db.scalars(select(Project).where(Project.userId == user_id)).all()


def get_user_max_competitors_per_project(db: Session, user_id: str) -> int:
    projects = get_user_projects(db, user_id)
    if not projects:
        return 0
    return max(count_project_competitors(db, project.id) for project in projects)


def build_usage_snapshot(db: Session, user: User) -> dict:
    effective_plan_key = get_effective_plan_key(user)
    selected_plan_key = get_plan_key(user)
    limits = get_user_plan_limits(user)

    return {
        "plan": selected_plan_key,
        "effectivePlan": effective_plan_key,
        "subscriptionStatus": get_subscription_status(user),
        "trialStartsAt": user.trialStartsAt.isoformat() if user.trialStartsAt else None,
        "trialEndsAt": user.trialEndsAt.isoformat() if user.trialEndsAt else None,
        "trialDays": get_trial_days(),
        "creditBalance": round(getattr(user, "creditBalance", 0.0) or 0.0, 2),
        "pendingPlanChange": getattr(user, "pendingPlanChange", None),
        "usage": {
            "projects": count_user_projects(db, user.id),
            "keywords": count_user_keywords(db, user.id),
            "reportsThisMonth": count_user_reports_this_month(db, user.id),
            "maxCompetitorsPerProject": get_user_max_competitors_per_project(db, user.id),
        },
        "limits": {
            "projects": limits["projects"],
            "keywords": limits["keywords"],
            "competitorsPerProject": limits["competitorsPerProject"],
            "reportsPerMonth": limits["reportsPerMonth"],
            "teamMembers": limits["teamMembers"],
            "dashboardCompetitorsPreview": limits["dashboardCompetitorsPreview"],
        },
    }


def is_downgrade(current_plan: str, target_plan: str) -> bool:
    return PLAN_ORDER.get(target_plan, 0) < PLAN_ORDER.get(current_plan, 0)


def build_downgrade_violations(db: Session, user: User, target_plan_key: str) -> list[dict]:
    target_limits = PLAN_DEFINITIONS[target_plan_key]["limits"]

    used_projects = count_user_projects(db, user.id)
    used_keywords = count_user_keywords(db, user.id)
    used_reports = count_user_reports_this_month(db, user.id)
    used_max_competitors = get_user_max_competitors_per_project(db, user.id)

    violations = []

    if used_projects > target_limits["projects"]:
        violations.append({
            "resource": "projects",
            "used": used_projects,
            "allowed": target_limits["projects"],
            "remove": used_projects - target_limits["projects"],
        })

    if used_keywords > target_limits["keywords"]:
        violations.append({
            "resource": "keywords",
            "used": used_keywords,
            "allowed": target_limits["keywords"],
            "remove": used_keywords - target_limits["keywords"],
        })

    if used_reports > target_limits["reportsPerMonth"]:
        violations.append({
            "resource": "reportsThisMonth",
            "used": used_reports,
            "allowed": target_limits["reportsPerMonth"],
            "remove": used_reports - target_limits["reportsPerMonth"],
        })

    if used_max_competitors > target_limits["competitorsPerProject"]:
        violations.append({
            "resource": "competitorsPerProject",
            "used": used_max_competitors,
            "allowed": target_limits["competitorsPerProject"],
            "remove": used_max_competitors - target_limits["competitorsPerProject"],
        })

    return violations


def validate_plan_change(db: Session, user: User, target_plan_key: str) -> dict:
    target_plan_key = (target_plan_key or "").strip().lower()
    if target_plan_key not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")

    current_plan = get_plan_key(user)
    downgrade = is_downgrade(current_plan, target_plan_key)
    violations = build_downgrade_violations(db, user, target_plan_key) if downgrade else []

    return {
        "allowed": len(violations) == 0,
        "isDowngrade": downgrade,
        "isUpgrade": PLAN_ORDER.get(target_plan_key, 0) > PLAN_ORDER.get(current_plan, 0),
        "currentPlan": current_plan,
        "targetPlan": target_plan_key,
        "violations": violations,
        "usage": build_usage_snapshot(db, user)["usage"],
        "limits": PLAN_DEFINITIONS[target_plan_key]["limits"],
    }


def change_user_plan(db: Session, user_id: str, plan_key: str) -> User:
    plan = (plan_key or "").strip().lower()
    if plan not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")

    user = get_user_or_404(db, user_id)
    validation = validate_plan_change(db, user, plan)

    if validation["isDowngrade"] and not validation["allowed"]:
        raise ApiError(409, "Downgrade not allowed until usage is reduced", validation)

    if validation["isDowngrade"]:
        user.pendingPlanChange = plan
        db.add(user)
        db.commit()
        db.refresh(user)
        
        create_notification(
            db,
            user_id=user.id,
            title="Plan downgrade scheduled",
            message=f"Your plan will be changed to {PLAN_DEFINITIONS[plan]['name']} at the end of your current billing period.",
            type="plan_change",
            severity="info",
        )
        db.commit()
        
        return user

    user.selectedPlan = plan
    user.subscriptionStatus = "active"

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def activate_paid_plan(db: Session, user_id: str, plan_key: str) -> User:
    plan = (plan_key or "").strip().lower()
    if plan not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")

    user = get_user_or_404(db, user_id)
    validation = validate_plan_change(db, user, plan)

    if validation["isDowngrade"] and not validation["allowed"]:
        raise ApiError(409, "Downgrade not allowed until usage is reduced", validation)

    user.selectedPlan = plan
    user.subscriptionStatus = "active"

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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