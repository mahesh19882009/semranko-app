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
    list_available_plans,
    validate_plan_change,
)

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/plans")
def get_plans() -> dict:
    return ok("Plans fetched", list_available_plans())


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
    })