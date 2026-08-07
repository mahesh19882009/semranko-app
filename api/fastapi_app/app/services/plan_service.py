import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import GST_RATE, get_settings
from app.core.errors import ApiError
from app.db.models import Competitor, Keyword, KeywordList, Project, Subscription, User, AIOTracking, KeywordListItem

logger = logging.getLogger(__name__)
settings = get_settings()

def _get_plan_defaults(plan_key: str) -> dict:
    base = {
        "free_trial": {"monthlyPrice": 0, "yearlyPrice": 0, "domain_limit": 0, "monthlyCredits": 100, "keywordLimit": 5, "competitorSpyLimit": 5, "competitorsPerProject": 3, "reportsPerMonth": 2, "teamMembers": 1, "weeklyTrackingEnabled": False},
        "starter": {"monthlyPrice": 999, "yearlyPrice": 10789, "domain_limit": 1, "monthlyCredits": 6000, "keywordLimit": 100, "competitorSpyLimit": 50, "competitorsPerProject": 3, "reportsPerMonth": 5, "teamMembers": 2, "weeklyTrackingEnabled": True},
        "pro": {"monthlyPrice": 3999, "yearlyPrice": 43189, "domain_limit": 5, "monthlyCredits": 30000, "keywordLimit": 500, "competitorSpyLimit": 200, "competitorsPerProject": 10, "reportsPerMonth": 10, "teamMembers": 5, "weeklyTrackingEnabled": True},
        "agency": {"monthlyPrice": 9999, "yearlyPrice": 107989, "domain_limit": 20, "monthlyCredits": 80000, "keywordLimit": 1500, "competitorSpyLimit": 500, "competitorsPerProject": 20, "reportsPerMonth": 50, "teamMembers": 10, "weeklyTrackingEnabled": True},
        "enterprise": {"monthlyPrice": 0, "yearlyPrice": 0, "domain_limit": 999, "monthlyCredits": 999999, "keywordLimit": 999999, "competitorSpyLimit": 5000, "competitorsPerProject": 999, "reportsPerMonth": 999, "teamMembers": 999, "weeklyTrackingEnabled": True},
    }
    return base.get(plan_key, base["free_trial"])

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
        **_get_plan_defaults("free_trial"),
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
        **_get_plan_defaults("starter"),
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
        **_get_plan_defaults("pro"),
    },
    "agency": {
        "key": "agency",
        "name": "Agency",
        "monthlyPrice": 9999,
        "yearlyPrice": 107989,
        "description": "Built for agencies handling multiple clients and organized client delivery.",
        "highlighted": False,
        "cta": "Start Agency",
        "refreshFrequency": "weekly",
        "individual_discount_pct": 15,
        **_get_plan_defaults("agency"),
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
        **_get_plan_defaults("enterprise"),
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
            "limits": get_user_plan_limits(plan),
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
    return get_user_plan_limits_from_plan(plan)


def get_user_plan_limits_from_plan(plan: dict) -> dict:
    limit_keys = [
        "competitorsPerProject",
        "reportsPerMonth",
        "teamMembers",
        "monthlyCredits",
        "competitorSpyLimit",
        "weeklyTrackingEnabled",
        "keywordLimit",
    ]
    return {k: plan.get(k) for k in limit_keys if k in plan}


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


def should_reset_credits(user: User) -> bool:
    """Check if user's credits should be reset based on plan anniversary."""
    plan_anniversary = getattr(user, "planAnniversaryAt", None)
    last_reset = getattr(user, "lastCreditResetAt", None)
    
    if not plan_anniversary:
        return False
    
    now = datetime.utcnow()
    
    # If never reset, check if we're past the first anniversary
    if not last_reset:
        return now >= plan_anniversary + timedelta(days=30)
    
    # Check if we're past the next anniversary (30-day cycles)
    next_anniversary = last_reset + timedelta(days=30)
    return now >= next_anniversary


def reset_monthly_credits(db: Session, user: User) -> dict:
    """Reset user's credits to their plan's monthly allocation (no rollover)."""
    if not should_reset_credits(user):
        return {"reset": False, "reason": "Not yet due for reset"}
    
    effective_plan_key = get_effective_plan_key(user)
    plan = PLAN_DEFINITIONS.get(effective_plan_key, PLAN_DEFINITIONS[TRIAL_PLAN_KEY])
    monthly_credits = plan.get("monthlyCredits", 0)
    
    # Reset credits (no rollover - previous balance is forfeited)
    user.creditBalance = float(monthly_credits)
    user.lastCreditResetAt = datetime.utcnow()
    
    # If this is the first reset, set the anniversary
    if not getattr(user, "planAnniversaryAt", None):
        user.planAnniversaryAt = datetime.utcnow()
    
    db.add(user)
    db.commit()
    
    logger.info(f"Reset credits for user {user.id} to {monthly_credits} (plan: {effective_plan_key})")
    
    return {
        "reset": True,
        "new_balance": monthly_credits,
        "plan": effective_plan_key,
        "reset_at": user.lastCreditResetAt.isoformat(),
    }


def set_plan_anniversary(db: Session, user: User) -> None:
    """Set the plan anniversary date for a user (called on plan activation/upgrade)."""
    if not getattr(user, "planAnniversaryAt", None):
        user.planAnniversaryAt = datetime.utcnow()
        user.lastCreditResetAt = datetime.utcnow()
        db.add(user)
        db.commit()
        logger.info(f"Set plan anniversary for user {user.id} to {user.planAnniversaryAt}")


def reset_due_credits_for_all_users(db: Session) -> dict:
    """Reset credits for all users who are due for their monthly reset (no rollover)."""
    from sqlalchemy import select
    
    users = db.scalars(select(User).where(User.subscriptionStatus == "active")).all()
    
    reset_count = 0
    skipped_count = 0
    total_credits_reset = 0
    
    for user in users:
        if should_reset_credits(user):
            result = reset_monthly_credits(db, user)
            if result.get("reset"):
                reset_count += 1
                total_credits_reset += result.get("new_balance", 0)
            else:
                skipped_count += 1
        else:
            skipped_count += 1
    
    return {
        "total_users": len(users),
        "reset_count": reset_count,
        "skipped_count": skipped_count,
        "total_credits_reset": total_credits_reset,
    }


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


def _get_warnings(db: Session, user: User, plan_def: dict) -> list[dict]:
    warnings = []
    now = datetime.utcnow()

    # Warning 1: Plan ending in 5 days
    end_date = None
    if user.trialEndsAt:
        end_date = user.trialEndsAt
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user.id,
            Subscription.isActive == True,
        )
    )
    if subscription and subscription.endDate:
        end_date = subscription.endDate

    if end_date:
        days_until_end = (end_date - now).days
        if 0 <= days_until_end <= 5:
            warnings.append({
                "type": "plan_ending_soon",
                "message": f"Your plan expires in {days_until_end} day(s). Please renew to avoid interruption.",
                "days_remaining": days_until_end,
            })

    # Warning 2: Low credit balance
    credit_balance = round(getattr(user, "creditBalance", 0.0) or 0.0, 2)
    monthly_credits = float(plan_def.get("monthlyCredits", 0))
    if monthly_credits > 0 and credit_balance < monthly_credits * 0.1:
        warnings.append({
            "type": "low_credit_balance",
            "message": f"Your credit balance ({credit_balance}) is low. Consider topping up or upgrading your plan.",
            "credit_balance": credit_balance,
        })

    # Warning 3: Insufficient credits for next operation (checked dynamically per operation)
    # This is handled at the operation level in credit_service.py

    return warnings


def build_usage_snapshot(db: Session, user: User) -> dict:
    effective_plan_key = get_effective_plan_key(user)
    selected_plan_key = get_plan_key(user)
    limits = get_user_plan_limits(user)
    plan_def = PLAN_DEFINITIONS.get(effective_plan_key, PLAN_DEFINITIONS[TRIAL_PLAN_KEY])

    subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user.id,
            Subscription.isActive == True
        )
    )

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
        "subscriptionStartDate": subscription.startDate.isoformat() if subscription and subscription.startDate else None,
        "subscriptionEndDate": subscription.endDate.isoformat() if subscription and subscription.endDate else None,
        "warnings": _get_warnings(db, user, plan_def),
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
    target_limits = get_user_plan_limits_from_plan(PLAN_DEFINITIONS[target_plan_key])

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

    now = datetime.utcnow()
    duration_days = 30

    user.selectedPlan = plan
    user.subscriptionStatus = "active"
    user.creditBalance = get_plan_monthly_credits(plan)

    existing_subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user_id,
            Subscription.isActive == True
        )
    )

    plan_id_map = {"starter": 0, "pro": 1, "agency": 2}
    effective_plan_id = plan_id_map.get(plan, 0)

    if existing_subscription:
        existing_subscription.planId = effective_plan_id
        existing_subscription.status = 'active'
        existing_subscription.isActive = True
        existing_subscription.startDate = now
        existing_subscription.endDate = now + timedelta(days=duration_days)
        db.add(existing_subscription)
    else:
        subscription = Subscription(
            userId=user_id,
            planId=effective_plan_id,
            status='active',
            isActive=True,
            startDate=now,
            endDate=now + timedelta(days=duration_days),
        )
        db.add(subscription)

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

    now = datetime.utcnow()
    duration_days = 30

    user.selectedPlan = plan
    user.subscriptionStatus = "active"
    user.creditBalance = get_plan_monthly_credits(plan)

    existing_subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user_id,
            Subscription.isActive == True
        )
    )

    plan_id_map = {"starter": 0, "pro": 1, "agency": 2}
    effective_plan_id = plan_id_map.get(plan, 0)

    if existing_subscription:
        existing_subscription.planId = effective_plan_id
        existing_subscription.status = 'active'
        existing_subscription.isActive = True
        existing_subscription.startDate = now
        existing_subscription.endDate = now + timedelta(days=duration_days)
        db.add(existing_subscription)
    else:
        subscription = Subscription(
            userId=user_id,
            planId=effective_plan_id,
            status='active',
            isActive=True,
            startDate=now,
            endDate=now + timedelta(days=duration_days),
        )
        db.add(subscription)

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
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)
    keyword_limit = limits.get("keywordLimit", 0)
    if keyword_limit <= 0:
        return
    used = count_user_keywords(db, user_id)
    if used >= keyword_limit:
        raise ApiError(403, f"Keyword limit reached. Your current plan allows {keyword_limit} keywords.")


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