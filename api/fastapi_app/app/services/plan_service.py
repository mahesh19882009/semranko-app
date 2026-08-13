import logging
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import GST_RATE, get_settings
from app.core.errors import ApiError
from app.db.models import Competitor, Keyword, KeywordList, Project, Subscription, User, KeywordListItem, PaymentOrder, CreditLedger
from app.services.credit_service import add_purchased_credits, deduct_credits, refund_credits

logger = logging.getLogger(__name__)
settings = get_settings()


def _plan_definition_to_dict(pd) -> dict:
    return {
        "key": pd.key,
        "name": pd.name,
        "monthlyPrice": pd.monthly_price_inr,
        "yearlyPrice": pd.yearly_price_inr,
        "domain_limit": pd.domain_limit,
        "monthlyCredits": pd.monthly_credits,
        "keywordLimit": pd.keyword_limit,
        "competitorSpyLimit": pd.competitor_spy_limit,
        "competitorsPerProject": pd.competitors_per_project,
        "reportsPerMonth": pd.reports_per_month,
        "weeklyTrackingEnabled": pd.key in {"starter", "pro", "agency", "enterprise"},
        "refreshFrequency": pd.refresh_frequency,
        "individual_discount_pct": pd.individual_discount_pct,
        "cta": pd.cta,
        "highlighted": pd.highlighted,
        "description": pd.description,
        "limits": {
            "competitorsPerProject": pd.competitors_per_project,
            "reportsPerMonth": pd.reports_per_month,
            "monthlyCredits": pd.monthly_credits,
            "competitorSpyLimit": pd.competitor_spy_limit,
            "weeklyTrackingEnabled": pd.key in {"starter", "pro", "agency", "enterprise"},
            "keywordLimit": pd.keyword_limit,
        },
    }


PLAN_DEFINITIONS = {k: _plan_definition_to_dict(v) for k, v in settings.plan_config.plans.items()}

PLAN_ORDER = {
    "free_trial": 0,
    "starter": 1,
    "pro": 2,
    "agency": 3,
    "enterprise": 4,
}

PLAN_ID_TO_KEY = {0: "starter", 1: "pro", 2: "agency", 3: "enterprise"}

TRIAL_PLAN_KEY = "free_trial"

GRACE_PERIOD_DAYS = 7


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
            "limits": get_user_plan_limits_from_plan(plan),
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
        "monthlyCredits",
        "competitorSpyLimit",
        "weeklyTrackingEnabled",
        "keywordLimit",
    ]
    return {k: plan.get(k) for k in limit_keys if k in plan}


def ensure_subscription_active(user: User) -> None:
    status = get_subscription_status(user)
    
    if status == "inactive":
        raise ApiError(403, "Your subscription is inactive. Please upgrade to continue.")
    
    if status == "past_due":
        raise ApiError(403, "Your subscription payment is past due. Please update your payment details.")
    
    if status not in {"trialing", "active"}:
        raise ApiError(403, "Your subscription is inactive. Please upgrade to continue.")

    trial_ends_at = getattr(user, "trialEndsAt", None)
    now = datetime.utcnow()
    
    if status == "trialing" and trial_ends_at:
        grace_period_end = trial_ends_at + timedelta(days=3)
        
        if trial_ends_at < now:
            if now < grace_period_end:
                pass
            else:
                raise ApiError(403, "Your trial has expired. Please upgrade to continue.")


def is_in_grace_period(user: User) -> bool:
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
    trial_ends_at = getattr(user, "trialEndsAt", None)
    if not trial_ends_at:
        return None
    
    return trial_ends_at + timedelta(days=3)


def set_plan_anniversary(db: Session, user: User) -> None:
    if not getattr(user, "planAnniversaryAt", None):
        user.planAnniversaryAt = datetime.utcnow()
        user.lastCreditResetAt = datetime.utcnow()
        db.add(user)
        db.commit()
        logger.info(f"Set plan anniversary for user {user.id} to {user.planAnniversaryAt}")


def should_reset_credits(user: User) -> bool:
    plan_anniversary = getattr(user, "planAnniversaryAt", None)
    last_reset = getattr(user, "lastCreditResetAt", None)
    
    if not plan_anniversary:
        return False
    
    now = datetime.utcnow()
    
    if not last_reset:
        return now >= plan_anniversary + timedelta(days=30)
    
    next_anniversary = last_reset + timedelta(days=30)
    return now >= next_anniversary


def reset_monthly_credits(db: Session, user: User) -> dict:
    if not should_reset_credits(user):
        return {"reset": False, "reason": "Not yet due for reset"}
    
    pending_plan = getattr(user, "pendingPlanChange", None)
    if pending_plan:
        pending_plan = pending_plan.strip().lower()
        if pending_plan not in PLAN_DEFINITIONS:
            user.pendingPlanChange = None
            db.add(user)
            db.commit()
            pending_plan = None
    
    effective_plan_key = pending_plan if pending_plan else get_effective_plan_key(user)
    plan = PLAN_DEFINITIONS.get(effective_plan_key, PLAN_DEFINITIONS[TRIAL_PLAN_KEY])
    monthly_credits = float(plan.get("monthlyCredits", 0))
    
    balance_before = round(float(getattr(user, "creditBalance", 0.0) or 0.0), 2)
    user.creditBalance = monthly_credits
    user.lastCreditResetAt = datetime.utcnow()
    
    if pending_plan:
        user.selectedPlan = pending_plan
        user.pendingPlanChange = None
        user.planAnniversaryAt = datetime.utcnow()
    
    db.add(user)
    db.commit()
    
    ledger = CreditLedger(
        userId=user.id,
        ownerId=user.id,
        amount=monthly_credits,
        actionType="monthly_refresh",
        description=f"Monthly credit refresh: {plan.get('name', effective_plan_key)} ({monthly_credits} credits)",
        status="completed",
        creditsReserved=0.0,
        creditsConsumed=0.0,
        creditsRefunded=0.0,
        netCreditChange=monthly_credits,
        balanceBefore=balance_before,
        balanceAfter=monthly_credits,
        planName=plan.get("name", effective_plan_key),
    )
    db.add(ledger)
    db.flush()
    db.commit()
    
    logger.info(f"Reset credits for user {user.id} to {monthly_credits} (plan: {effective_plan_key})")
    
    return {
        "reset": True,
        "new_balance": monthly_credits,
        "plan": effective_plan_key,
        "reset_at": user.lastCreditResetAt.isoformat(),
    }


def reset_due_credits_for_all_users(db: Session) -> dict:
    users = db.scalars(select(User).where(User.subscriptionStatus == "active")).all()
    
    reset_count = 0
    skipped_count = 0
    total_credits_reset = 0
    errors = []
    
    for user in users:
        try:
            now = datetime.utcnow()
            plan_anniversary = getattr(user, "planAnniversaryAt", None)
            last_reset = getattr(user, "lastCreditResetAt", None)
            
            if not plan_anniversary:
                skipped_count += 1
                continue
            
            if not last_reset:
                next_anniversary = plan_anniversary + timedelta(days=30)
            else:
                next_anniversary = last_reset + timedelta(days=30)
            
            if now < next_anniversary:
                skipped_count += 1
                continue
            
            pending_plan = getattr(user, "pendingPlanChange", None)
            if pending_plan:
                pending_plan = pending_plan.strip().lower()
                if pending_plan not in PLAN_DEFINITIONS:
                    pending_plan = None
            
            effective_plan_key = pending_plan if pending_plan else get_effective_plan_key(user)
            plan = PLAN_DEFINITIONS.get(effective_plan_key, PLAN_DEFINITIONS[TRIAL_PLAN_KEY])
            monthly_credits = float(plan.get("monthlyCredits", 0))
            
            balance_before = round(float(getattr(user, "creditBalance", 0.0) or 0.0), 2)
            user.creditBalance = monthly_credits
            user.lastCreditResetAt = now
            
            if pending_plan:
                user.selectedPlan = pending_plan
                user.pendingPlanChange = None
                user.planAnniversaryAt = now
            
            db.add(user)
            db.commit()
            
            ledger = CreditLedger(
                userId=user.id,
                ownerId=user.id,
                amount=monthly_credits,
                actionType="monthly_refresh",
                description=f"Monthly credit refresh: {plan.get('name', effective_plan_key)} ({monthly_credits} credits)",
                status="completed",
                creditsReserved=0.0,
                creditsConsumed=0.0,
                creditsRefunded=0.0,
                netCreditChange=monthly_credits,
                balanceBefore=balance_before,
                balanceAfter=monthly_credits,
                planName=plan.get("name", effective_plan_key),
            )
            db.add(ledger)
            db.flush()
            db.commit()
            
            logger.info(f"Reset credits for user {user.id} to {monthly_credits} (plan: {effective_plan_key})")
            reset_count += 1
            total_credits_reset += monthly_credits
        except Exception as exc:
            logger.error(f"Monthly credit refresh failed for user {user.id}: {exc}")
            errors.append({"user_id": user.id, "error": str(exc)})
            skipped_count += 1
    
    return {
        "total_users": len(users),
        "reset_count": reset_count,
        "skipped_count": skipped_count,
        "total_credits_reset": total_credits_reset,
        "errors": errors,
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


def count_user_active_keywords(db: Session, user_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Keyword)
        .join(Project, Keyword.projectId == Project.id)
        .where(Project.userId == user_id, Keyword.isActive == True)
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

    credit_balance = round(getattr(user, "creditBalance", 0.0) or 0.0, 2)
    monthly_credits = float(plan_def.get("monthlyCredits", 0))
    if monthly_credits > 0 and credit_balance < monthly_credits * 0.1:
        warnings.append({
            "type": "low_credit_balance",
            "message": f"Your credit balance ({credit_balance}) is low. Consider topping up or upgrading your plan.",
            "credit_balance": credit_balance,
        })

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
        "lastCreditResetAt": user.lastCreditResetAt.isoformat() if getattr(user, "lastCreditResetAt", None) else None,
        "nextCreditResetAt": (user.lastCreditResetAt + timedelta(days=30)).isoformat() if getattr(user, "lastCreditResetAt", None) else ((user.planAnniversaryAt + timedelta(days=30)).isoformat() if getattr(user, "planAnniversaryAt", None) else None),
        "warnings": _get_warnings(db, user, plan_def),
        "usage": {
            "projects": count_user_projects(db, user.id),
            "keywords": count_user_keywords(db, user.id),
            "activeKeywords": count_user_active_keywords(db, user.id),
            "maxCompetitorsPerProject": get_user_max_competitors_per_project(db, user.id),
        },
        "limits": {
            "competitorsPerProject": limits["competitorsPerProject"],
            "reportsPerMonth": limits["reportsPerMonth"],
            "keywordResearchCreditsPerMonth": limits.get("keywordResearchCreditsPerMonth", 0),
            "monthlyCredits": limits.get("monthlyCredits", 0),
            "keywordLimit": limits.get("keywordLimit"),
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


def is_upgrade(current_plan: str, target_plan: str) -> bool:
    return PLAN_ORDER.get(target_plan, 0) > PLAN_ORDER.get(current_plan, 0)


def build_downgrade_violations(db: Session, user: User, target_plan_key: str) -> list[dict]:
    target_limits = get_user_plan_limits_from_plan(PLAN_DEFINITIONS[target_plan_key])

    total_keywords = count_user_keywords(db, user.id)
    used_max_competitors = get_user_max_competitors_per_project(db, user.id)
    used_projects = count_user_projects(db, user.id)

    violations = []

    if total_keywords > target_limits["keywordLimit"]:
        violations.append({
            "resource": "keywordLimit",
            "used": total_keywords,
            "allowed": target_limits["keywordLimit"],
            "remove": total_keywords - target_limits["keywordLimit"],
        })

    if used_max_competitors > target_limits["competitorsPerProject"]:
        violations.append({
            "resource": "competitorsPerProject",
            "used": used_max_competitors,
            "allowed": target_limits["competitorsPerProject"],
            "remove": used_max_competitors - target_limits["competitorsPerProject"],
        })

    target_domain_limit = PLAN_DEFINITIONS[target_plan_key].get("domain_limit", 0)
    if target_domain_limit > 0 and used_projects > target_domain_limit:
        violations.append({
            "resource": "domain_limit",
            "used": used_projects,
            "allowed": target_domain_limit,
            "remove": used_projects - target_domain_limit,
        })

    return violations


def validate_plan_change(db: Session, user: User, target_plan_key: str) -> dict:
    target_plan_key = (target_plan_key or "").strip().lower()
    if target_plan_key not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")

    current_plan = get_plan_key(user)
    downgrade = is_downgrade(current_plan, target_plan_key)
    upgrade = is_upgrade(current_plan, target_plan_key)
    violations = build_downgrade_violations(db, user, target_plan_key) if downgrade else []

    return {
        "allowed": len(violations) == 0,
        "isDowngrade": downgrade,
        "isUpgrade": upgrade,
        "isSamePlan": current_plan == target_plan_key,
        "currentPlan": current_plan,
        "targetPlan": target_plan_key,
        "violations": violations,
        "usage": build_usage_snapshot(db, user)["usage"],
        "limits": PLAN_DEFINITIONS[target_plan_key]["limits"],
    }


def get_plan_monthly_credits(plan_key: str) -> float:
    plan = PLAN_DEFINITIONS.get(plan_key, {})
    return float(plan.get("monthlyCredits", 0))


def get_billing_cycle_days(billing_cycle: str) -> int:
    return 365 if billing_cycle == "yearly" else 30


def _record_subscription_ledger(
    db: Session,
    user_id: str,
    amount: float,
    action_type: str,
    description: str,
    related_order_id: str | None = None,
    balance_before: float | None = None,
    balance_after: float | None = None,
) -> None:
    try:
        user = db.scalar(select(User).where(User.id == user_id))
        if not user:
            return
        
        if balance_before is None:
            balance_before = round(float(getattr(user, "creditBalance", 0.0) or 0.0), 2)
        if balance_after is None:
            balance_after = round(balance_before + amount, 2) if amount >= 0 else round(balance_before - abs(amount), 2)
        
        ledger = CreditLedger(
            userId=user_id,
            ownerId=user_id,
            amount=amount,
            actionType=action_type,
            description=description,
            relatedOrderId=related_order_id,
            status="success",
            creditsReserved=0.0,
            creditsConsumed=float(abs(amount)) if amount < 0 else 0.0,
            creditsRefunded=0.0,
            netCreditChange=float(amount),
            balanceBefore=balance_before,
            balanceAfter=balance_after,
        )
        db.add(ledger)
        db.flush()
    except Exception as exc:
        logger.error(f"Failed to record subscription ledger for user {user_id}: {exc}")


def handle_expiration(db: Session, user: User) -> None:
    if getattr(user, "subscriptionStatus", None) == "past_due":
        return
    
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user.id,
            Subscription.isActive == True
        )
    )
    
    if not subscription or not subscription.endDate:
        return
    
    now = datetime.utcnow()
    if subscription.endDate >= now:
        return
    
    user.subscriptionStatus = "past_due"
    db.add(user)
    db.commit()
    logger.info(f"Subscription expired for user {user.id}, status set to past_due")


def handle_grace_period_expiry(db: Session, user: User) -> None:
    if getattr(user, "subscriptionStatus", None) != "past_due":
        return
    
    subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user.id,
            Subscription.isActive == True
        )
    )
    
    if not subscription or not subscription.endDate:
        return
    
    grace_period_end = subscription.endDate + timedelta(days=GRACE_PERIOD_DAYS)
    now = datetime.utcnow()
    
    if now >= grace_period_end:
        user.subscriptionStatus = "inactive"
        db.add(user)
        db.commit()
        
        deactivate_user_keywords(db, user.id)
        logger.info(f"Grace period expired for user {user.id}, status set to inactive, keywords deactivated")


def deactivate_user_keywords(db: Session, user_id: str) -> None:
    keywords = db.scalars(
        select(Keyword).join(Project, Project.id == Keyword.projectId).where(
            Project.userId == user_id,
            Keyword.isActive == True
        )
    ).all()
    
    for kw in keywords:
        kw.isActive = False
        db.add(kw)
    
    db.commit()
    logger.info(f"Deactivated {len(keywords)} keywords for user {user_id}")


def reactivate_subscription(db: Session, user_id: str, plan_key: str, order_id: str | None = None) -> User:
    plan = (plan_key or "").strip().lower()
    if plan not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")
    
    user = get_user_or_404(db, user_id)
    
    now = datetime.utcnow()
    duration_days = 30
    monthly_credits = float(PLAN_DEFINITIONS.get(plan, {}).get("limits", {}).get("monthlyCredits", 0))
    old_balance = float(getattr(user, "creditBalance", 0.0) or 0.0)
    
    user.selectedPlan = plan
    user.subscriptionStatus = "active"
    user.creditBalance = float(monthly_credits)
    user.planAnniversaryAt = now
    user.lastCreditResetAt = now
    
    existing_subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user_id,
            Subscription.isActive == True
        )
    )
    
    plan_id_map = {"starter": 0, "pro": 1, "agency": 2, "enterprise": 3}
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
    
    _record_subscription_ledger(
        db=db,
        user_id=user_id,
        amount=float(monthly_credits),
        action_type="purchase",
        description=f"Reactivation: {plan} (Order {order_id or 'N/A'})",
        related_order_id=order_id,
        balance_before=old_balance,
    )
    db.commit()
    
    return user


def change_user_plan(db: Session, user_id: str, plan_key: str) -> User:
    plan = (plan_key or "").strip().lower()
    if plan not in PLAN_DEFINITIONS:
        raise ApiError(400, "Invalid plan")

    user = get_user_or_404(db, user_id)
    validation = validate_plan_change(db, user, plan)

    if validation["isDowngrade"] and not validation["allowed"]:
        raise ApiError(409, "Downgrade not allowed until usage is reduced", validation)

    current_plan = get_plan_key(user)
    if current_plan == plan:
        return user

    user.pendingPlanChange = plan
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
    monthly_credits = float(PLAN_DEFINITIONS.get(plan, {}).get("limits", {}).get("monthlyCredits", 0))
    old_balance = float(getattr(user, "creditBalance", 0.0) or 0.0)

    user.selectedPlan = plan
    user.subscriptionStatus = "active"
    user.creditBalance = float(monthly_credits)
    user.planAnniversaryAt = now
    user.lastCreditResetAt = now

    existing_subscription = db.scalar(
        select(Subscription).where(
            Subscription.userId == user_id,
            Subscription.isActive == True
        )
    )

    plan_id_map = {"starter": 0, "pro": 1, "agency": 2, "enterprise": 3}
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
    
    action_type = "upgrade" if validation["isUpgrade"] else ("downgrade" if validation["isDowngrade"] else "plan_change")
    _record_subscription_ledger(
        db=db,
        user_id=user_id,
        amount=float(monthly_credits),
        action_type=action_type,
        description=f"Paid plan activation: {plan} - {PLAN_DEFINITIONS.get(plan, {}).get('name', plan)}",
        related_order_id=None,
        balance_before=old_balance,
    )
    db.commit()
    
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
    limits = get_user_plan_limits(user)
    domain_limit = limits.get("domain_limit", 0)
    if domain_limit <= 0:
        return
    if used >= domain_limit:
        raise ApiError(403, f"Domain limit reached. Your current plan allows {domain_limit} domain(s).")


def ensure_keyword_limit(db: Session, user_id: str) -> None:
    user = get_user_or_404(db, user_id)
    ensure_subscription_active(user)
    limits = get_user_plan_limits(user)
    keyword_limit = limits.get("keywordLimit", 0)
    if keyword_limit <= 0:
        return
    used = db.scalar(
        select(func.count())
        .select_from(Keyword)
        .join(Project, Keyword.projectId == Project.id)
        .where(Project.userId == user_id)
        .where(or_(Keyword.isActive == True, Keyword.deletedAt.is_(None)))
    ) or 0
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


def activate_keyword(db: Session, user_id: str, keyword_id: str) -> Keyword:
    keyword = db.scalar(
        select(Keyword).join(Project, Project.id == Keyword.projectId).where(
            Keyword.id == keyword_id,
            Project.userId == user_id,
        )
    )
    if not keyword:
        raise ApiError(404, "Keyword not found")
    
    if keyword.isActive:
        return keyword
    
    keyword.isActive = True
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


def deactivate_keyword(db: Session, user_id: str, keyword_id: str) -> Keyword:
    keyword = db.scalar(
        select(Keyword).join(Project, Project.id == Keyword.projectId).where(
            Keyword.id == keyword_id,
            Project.userId == user_id,
        )
    )
    if not keyword:
        raise ApiError(404, "Keyword not found")
    
    if not keyword.isActive:
        return keyword
    
    keyword.isActive = False
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword
