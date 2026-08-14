from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.plan_service import (
    build_usage_snapshot,
    change_user_plan,
    get_user_or_404,
    is_in_grace_period,
    get_grace_period_end,
    get_credit_costs,
    validate_plan_change,
)
from app.services.commercial_config_service import plan_definitions, serialize_top_up, list_top_up_packages

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/plans")
def get_plans(db: Session = Depends(db_session)) -> dict:
    plans = plan_definitions(db)
    return ok("Plans fetched", [
        {**plan, "limits": plan["limits"], "creditCosts": get_credit_costs()}
        for plan in plans.values() if plan["key"] != "enterprise"
    ])


@router.get("/top-up-packages")
def get_top_up_packages(db: Session = Depends(db_session)) -> dict:
    return ok("Top-up packages fetched", [serialize_top_up(package) for package in list_top_up_packages(db)])


@router.get("/current")
def get_current_pricing(
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    db_user = get_user_or_404(db, user["userId"])
    snapshot = build_usage_snapshot(db, db_user)
    return ok("Current pricing fetched", snapshot)


@router.get("/downgrade-check")
def get_downgrade_check(
    plan: str = Query(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    db_user = get_user_or_404(db, user["userId"])
    result = validate_plan_change(db, db_user, str(plan).strip().lower())
    return ok("Plan change validation fetched", result)


@router.post("/change-plan")
def change_plan(
    payload: dict = Body(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    plan_key = str(payload.get("plan", "")).strip().lower()
    updated = change_user_plan(db, user["userId"], plan_key)
    snapshot = build_usage_snapshot(db, updated)
    return ok("Plan changed successfully", snapshot)


@router.get("/subscription-status")
def get_subscription_status(
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    """Get detailed subscription status including grace period information."""
    db_user = get_user_or_404(db, user["userId"])
    snapshot = build_usage_snapshot(db, db_user)
    
    return ok("Subscription status fetched", {
        "plan": snapshot["plan"],
        "effectivePlan": snapshot["effectivePlan"],
        "subscriptionStatus": snapshot["subscriptionStatus"],
        "pendingPlanChange": snapshot["pendingPlanChange"],
        "trialStartsAt": snapshot["trialStartsAt"],
        "trialEndsAt": snapshot["trialEndsAt"],
        "subscriptionStartDate": snapshot["subscriptionStartDate"],
        "subscriptionEndDate": snapshot["subscriptionEndDate"],
        "gracePeriodEndsAt": snapshot["gracePeriodEndsAt"],
        "isInGracePeriod": snapshot["isInGracePeriod"],
        "trialDays": snapshot["trialDays"],
        "usage": snapshot["usage"],
        "limits": snapshot["limits"],
        "creditBalance": snapshot["creditBalance"],
        "totalMonthlyAllocation": snapshot["totalMonthlyAllocation"],
        "spendableCreditsRemaining": snapshot["spendableCreditsRemaining"],
        "planSpendableCreditsRemaining": snapshot["planSpendableCreditsRemaining"],
        "purchasedCreditsRemaining": snapshot["purchasedCreditsRemaining"],
        "automaticReservedAllocation": snapshot["automaticReservedAllocation"],
        "automaticReservedRemaining": snapshot["automaticReservedRemaining"],
        "nextCreditResetAt": snapshot["nextCreditResetAt"],
        "featureUsage": snapshot["featureUsage"],
        "creditCosts": snapshot["creditCosts"],
    })
