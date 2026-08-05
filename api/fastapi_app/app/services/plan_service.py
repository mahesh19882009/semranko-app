from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import GST_RATE, get_settings
from app.core.errors import ApiError
from app.db.models import Competitor, Keyword, KeywordList, Project, Subscription, User, AIOTracking, KeywordListItem

PLAN_DEFINITIONS = {
    "free_trial": {
        "key": "free_trial",
        "name": "Free Trial",
        "monthlyPrice": 0,
        "yearlyPrice": 0,
        "description": "7-day free trial to test RankCare.",
        "highlighted": False,
        "cta": "Start Free Trial",
        "refreshFrequency": "weekly",
        "individual_discount_pct": 0,
        "domain_limit": 0,
        "limits": {
            "competitorsPerProject": 3,
            "reportsPerMonth": 1,
            "teamMembers": 1,
            "monthlyCredits": 200,
            "competitorSpyLimit": 20,
            "weeklyTrackingEnabled": False,
        },
    },
    "starter": {
        "key": "starter",
        "name": "Starter",
        "monthlyPrice": 999,
        "yearlyPrice": 10789,
        "description": "Best for freelancers and small websites starting SEO tracking.",
        "highlighted": False,
        "cta": "Start Starter",
        "refreshFrequency": "weekly",
        "individual_discount_pct": 0,
        "domain_limit": 1,
        "limits": {
            "competitorsPerProject": 3,
            "reportsPerMonth": 1,
            "teamMembers": 1,
            "monthlyCredits": 2000,
            "competitorSpyLimit": 100,
            "weeklyTrackingEnabled": True,
        },
    },
    "pro": {
        "key": "pro",
        "name": "Pro",
        "monthlyPrice": 3999,
        "yearlyPrice": 43189,
        "description": "Ideal for growing businesses that need stronger reporting and tracking.",
        "highlighted": True,
        "cta": "Start Pro",
        "refreshFrequency": "weekly",
        "individual_discount_pct": 10,
        "domain_limit": 5,
        "limits": {
            "competitorsPerProject": 10,
            "reportsPerMonth": 10,
            "teamMembers": 3,
            "monthlyCredits": 8000,
            "competitorSpyLimit": 300,
            "weeklyTrackingEnabled": True,
        },
    },
    "agency": {
        "key": "agency",
        "name": "Agency",
        "monthlyPrice": 15999,
        "yearlyPrice": 172789,
        "description": "Built for agencies handling multiple clients and organized client delivery.",
        "highlighted": False,
        "cta": "Start Agency",
        "refreshFrequency": "weekly",
        "individual_discount_pct": 15,
        "domain_limit": 20,
        "limits": {
            "competitorsPerProject": 20,
            "reportsPerMonth": 50,
            "teamMembers": 10,
            "monthlyCredits": 32000,
            "competitorSpyLimit": 1000,
            "weeklyTrackingEnabled": True,
        },
    },
    "enterprise": {
        "key": "enterprise",
        "name": "Enterprise",
        "monthlyPrice": 0,
        "yearlyPrice": 0,
        "description": "Custom bulk allocation for large teams. Contact sales for pricing.",
        "highlighted": False,
        "cta": "Contact Sales",
        "refreshFrequency": "weekly",
        "individual_discount_pct": 0,
        "domain_limit": 999,
        "limits": {
            "projects": 999,
            "competitorsPerProject": 999,
            "reportsPerMonth": 999,
            "teamMembers": 999,
            "monthlyCredits": 999999,
            "competitorSpyLimit": 5000,
            "weeklyTrackingEnabled": True,
        },
    },
}

PLAN_ORDER = {
    "free_trial": 0,
    "starter": 1,
    "pro": 2,
    "agency": 3,
}

PLAN_ID_TO_KEY = {0: "starter", 1: "pro", 2: "agency"}

TRIAL_PLAN_KEY = "free_trial"


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
            "refreshFrequency": plan.get("refreshFrequency", "weekly"),
            "individual_discount_pct": plan.get("individual_discount_pct", 0),
            "base_price_inr": plan["monthlyPrice"],
            "domain_limit": plan.get("domain_limit", 0),
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
    plan = getattr(user, "selectedPlan", None)
    if not plan or plan.strip() == "":
        return "free_trial"
    return plan.strip().lower()


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
    
    # Allow active and trialing subscriptions
    if status not in {"trialing", "active"}:
        raise ApiError(403, "Your subscription is inactive. Please upgrade to continue.")

    trial_ends_at = getattr(user, "trialEndsAt", None)
    now = datetime.utcnow()
    
    if status == "trialing" and trial_ends_at:
        # Calculate grace period end (3 days after trial expiration)
        grace_period_end = trial_ends_at + timedelta(days=3)
        
        if trial_ends_at < now:
            if now < grace_period_end:
                # Within grace period - allow access but could show warning
                pass
            else:
                # Grace period expired - block access
                raise ApiError(403, "Your trial has expired. Please upgrade to continue.")


def is_in_grace_period(user: User) -> bool:
    """Check if user is in trial grace period (trial expired but within 3-day grace window)."""
    trial_ends_at = getattr(user, "trialEndsAt", None)
    if not trial_ends_at:
        return False
    
    status = get_subscription_status(user)
    if status != "trialing":
        return False
    
    now = datetime.utcnow()
    grace_period_end = trial_ends_at + timedelta(days=3)
    
    return trial_ends_at < now < grace_period_end


def get_grace_period_end(user: User) -> Optional[datetime]:
    """Get the grace period end date for a user, or None if not applicable."""
    trial_ends_at = getattr(user, "trialEndsAt", None)
    if not trial_ends_at:
        return None
    
    return trial_ends_at + timedelta(days=3)


def count_user_projects(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Project).where(Project.userId == user_id)
    ) or 0


def count_user_keywords(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Keyword)
        .join(Project, Keyword.projectId == Project.id)
        .where(Project.userId == user_id)
    ) or 0


def count_project_competitors(db: Session, project_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Competitor).where(Competitor.projectId == project_id)
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
    plan_def = PLAN_DEFINITIONS.get(effective_plan_key, PLAN_DEFINITIONS[TRIAL_PLAN_KEY])

    return {
        "plan": selected_plan_key,
        "effectivePlan": effective_plan_key,
        "subscriptionStatus": get_subscription_status(user),
        "trialStartsAt": user.trialStartsAt.isoformat() if user.trialStartsAt else None,
        "trialEndsAt": user.trialEndsAt.isoformat() if user.trialEndsAt else None,
        "gracePeriodEndsAt": get_grace_period_end(user).isoformat() if get_grace_period_end(user) else None,
        "isInGracePeriod": is_in_grace_period(user),
        "trialDays": get_trial_days(),
        "creditBalance": round(getattr(user, "creditBalance", 0.0) or 0.0, 2),
        "base_price_inr": plan_def.get("monthlyPrice", 0),
        "individual_discount_pct": plan_def.get("individual_discount_pct", 0),
        "usage": {
            "projects": count_user_projects(db, user.id),
            "keywords": count_user_keywords(db, user.id),
            "maxCompetitorsPerProject": get_user_max_competitors_per_project(db, user.id),
        },
        "limits": {
            "competitorsPerProject": limits["competitorsPerProject"],
            "reportsPerMonth": limits["reportsPerMonth"],
            "teamMembers": limits["teamMembers"],
            "keywordResearchCreditsPerMonth": limits.get("keywordResearchCreditsPerMonth", 0),
            "monthlyCredits": limits.get("monthlyCredits", 0),
            "domain_limit": plan_def.get("domain_limit", 0),
            "competitorSpyLimit": limits.get("competitorSpyLimit", 0),
        },
        "features": {
            "allow_exports": effective_plan_key in {"pro", "agency", "enterprise"},
            "allow_white_label": effective_plan_key in {"agency", "enterprise"},
            "competitor_spy_min_credits": 20,
        },
    }


def is_downgrade(current_plan: str, target_plan: str) -> bool:
    return PLAN_ORDER.get(target_plan, 0) < PLAN_ORDER.get(current_plan, 0)


def build_downgrade_violations(db: Session, user: User, target_plan_key: str) -> list[dict]:
    target_limits = PLAN_DEFINITIONS[target_plan_key]["limits"]

    used_max_competitors = get_user_max_competitors_per_project(db, user.id)

    violations = []

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


def get_plan_monthly_credits(plan_key: str) -> float:
    plan = PLAN_DEFINITIONS.get(plan_key, {})
    return float(plan.get("limits", {}).get("monthlyCredits", 0))


def change_user_plan(db: Session, user_id: str, plan_key: str) -> User:
    plan = (plan_key or "").strip().lower()
    if plan not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")

    user = get_user_or_404(db, user_id)
    validation = validate_plan_change(db, user, plan)

    if validation["isDowngrade"] and not validation["allowed"]:
        raise ApiError(409, "Downgrade not allowed until usage is reduced", validation)

    user.selectedPlan = plan
    user.subscriptionStatus = "active"
    user.creditBalance = get_plan_monthly_credits(plan)

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
    user.creditBalance = get_plan_monthly_credits(plan)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_domain_limit(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)
    domain_limit = limits.get("domain_limit", 0)
    if domain_limit <= 0:
        return
    used = count_user_projects(db, user_id)
    if used >= domain_limit:
        raise ApiError(403, f"Domain limit reached. Your current plan allows {domain_limit} domain(s).")


def ensure_project_limit(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    used = count_user_projects(db, user_id)
    if used == 0:
        return

    from app.services.credit_service import get_credit_balance, deduct_credits
    balance = get_credit_balance(db, user_id)
    if balance < 10:
        raise ApiError(403, "Insufficient credits to create a new project. Please upgrade or top up your credits.")

    deduct_credits(db, user_id, 10, "ADD_NEW_DOMAIN", "Created extra multi-domain project")


def ensure_keyword_limit(db: Session, user_id: str) -> None:
    return


def ensure_competitor_limit(db: Session, user_id: str, project_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)
    used = count_project_competitors(db, project_id)
    allowed = limits["competitorsPerProject"]
    if used >= allowed:
        raise ApiError(403, f"Competitor limit reached. Your current plan allows {allowed} competitor(s) per project.")


def get_user_plan_limits_by_id(db: Session, user_id: str) -> dict:
    user = get_user_or_404(db, user_id)
    return get_user_plan_limits(user)