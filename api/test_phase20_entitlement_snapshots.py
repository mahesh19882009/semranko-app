"""Behavioral coverage for Admin offerings versus immutable cycle entitlements."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.routes.admin_commercial import update_plan
from app.api.routes.payments import get_current_plan
from app.api.routes.pricing import get_current_pricing, get_plans
from app.core.errors import ApiError
from app.db.models import Base, Keyword, PlanCommercialConfig, Project, Subscription, SubscriptionEntitlementSnapshot, User
from app.services.auth_service import register_user
from app.services.commercial_config_service import active_entitlements, ensure_commercial_config, plan_definitions
from app.services.feature_usage_service import get_feature_usage
from app.services.payment_service import activate_subscription
from app.services.plan_service import apply_credit_cycle_allocation, ensure_keyword_limit, ensure_project_limit, handle_grace_period_expiry, reset_monthly_credits


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db, user_id, plan="starter", admin=False):
    now = datetime.utcnow().replace(microsecond=0)
    user = User(id=user_id, name=user_id, email=f"{user_id}@example.com", passwordHash="hash", isAdmin=admin,
                selectedPlan=plan, subscriptionStatus="active" if plan != "free_trial" else "free",
                planAnniversaryAt=now, lastCreditResetAt=now)
    db.add(user); db.commit()
    return user


def test_admin_change_updates_offering_but_not_active_snapshot_and_new_user_gets_it():
    db = make_db(); admin = make_user(db, "admin", admin=True); existing = make_user(db, "existing")
    apply_credit_cycle_allocation(db, existing, "starter", now=existing.lastCreditResetAt)
    assert active_entitlements(db, existing)["keywordLimit"] == 100

    update_plan("starter", {"keywordLimit": 150, "manualRefreshLimit": 20,
                            "keywordResearchLimit": 15, "competitorSpyLimit": 5}, db, admin)
    assert plan_definitions(db)["starter"]["keywordLimit"] == 150
    public_starter = next(plan for plan in get_plans(db)["data"] if plan["key"] == "starter")
    assert public_starter["keywordLimit"] == 150
    assert active_entitlements(db, existing)["keywordLimit"] == 100
    assert get_current_pricing({"userId": existing.id}, db)["data"]["limits"]["keywordLimit"] == 100
    assert asyncio.run(get_current_plan(existing, db))["data"]["limits"]["keywordLimit"] == 100
    assert get_feature_usage(db, existing.id, "manual_refresh")["limit"] == 10

    newcomer = make_user(db, "newcomer")
    apply_credit_cycle_allocation(db, newcomer, "starter", now=newcomer.lastCreditResetAt)
    entitlements = active_entitlements(db, newcomer)
    assert (entitlements["keywordLimit"], entitlements["manualRefreshLimit"],
            entitlements["keywordResearchLimit"], entitlements["competitorSpyLimit"]) == (150, 20, 15, 5)


def test_renewal_uses_current_credits_preserves_topups_and_is_idempotent():
    db = make_db(); admin = make_user(db, "admin", admin=True); user = make_user(db, "renew")
    apply_credit_cycle_allocation(db, user, "starter", now=user.lastCreditResetAt)
    old_snapshot_count = db.scalar(select(func.count()).select_from(SubscriptionEntitlementSnapshot))
    update_plan("starter", {"monthlyCredits": 9000, "automaticCredits": 5500,
                            "manualRefreshLimit": 17, "keywordResearchLimit": 18,
                            "competitorSpyLimit": 6}, db, admin)
    assert (user.planCreditBalance, user.automaticCreditBalance) == (3000, 5000)
    assert get_feature_usage(db, user.id, "manual_refresh")["limit"] == 10
    user.purchasedCreditBalance = 777; user.creditBalance = user.planCreditBalance + 777
    user.lastCreditResetAt = datetime.utcnow() - timedelta(days=31); db.commit()

    result = reset_monthly_credits(db, user)
    assert result["reset"] is True
    assert (user.planCreditBalance, user.automaticCreditBalance, user.purchasedCreditBalance) == (3500, 5500, 777)
    assert user.creditBalance == 4277
    assert get_feature_usage(db, user.id, "manual_refresh")["limit"] == 17
    assert get_feature_usage(db, user.id, "keyword_research")["limit"] == 18
    assert get_feature_usage(db, user.id, "competitor_spy")["limit"] == 6
    assert db.scalar(select(func.count()).select_from(SubscriptionEntitlementSnapshot)) == old_snapshot_count + 1
    assert reset_monthly_credits(db, user)["reset"] is False


def test_payment_renewal_uses_current_offering_and_duplicate_callback_is_idempotent():
    db = make_db(); admin = make_user(db, "admin", admin=True); user = make_user(db, "payment-renew")
    apply_credit_cycle_allocation(db, user, "starter", now=user.lastCreditResetAt)
    subscription = Subscription(userId=user.id, planId=0, status="active", isActive=True,
                                startDate=user.lastCreditResetAt, endDate=user.lastCreditResetAt + timedelta(days=30))
    db.add(subscription); db.commit()
    original_count = db.scalar(select(func.count()).select_from(SubscriptionEntitlementSnapshot))
    update_plan("starter", {"keywordLimit": 180, "monthlyCredits": 9200, "automaticCredits": 5600}, db, admin)
    user.purchasedCreditBalance = 444; user.creditBalance = user.planCreditBalance + 444; db.commit()

    with patch("app.services.payment_service.email_service.send_payment_success_email", return_value=True):
        first = activate_subscription(db, user.id, 0, "pay-renew", "order-renew")
        second = activate_subscription(db, user.id, 0, "pay-renew", "order-renew")

    db.refresh(user)
    assert first.id == second.id
    assert active_entitlements(db, user)["keywordLimit"] == 180
    assert (user.planCreditBalance, user.automaticCreditBalance, user.purchasedCreditBalance) == (3600, 5600, 444)
    assert user.creditBalance == 4044
    assert db.scalar(select(func.count()).select_from(SubscriptionEntitlementSnapshot)) == original_count + 1


def test_project_keyword_and_feature_enforcement_use_snapshot_not_new_offering():
    db = make_db(); admin = make_user(db, "admin", admin=True); user = make_user(db, "limits")
    ensure_commercial_config(db)
    row = db.scalar(select(PlanCommercialConfig).where(PlanCommercialConfig.planKey == "starter"))
    row.projectLimit = 1; row.keywordLimit = 1; row.manualRefreshLimit = 2; row.keywordResearchLimit = 3; row.competitorSpyLimit = 4; db.commit()
    apply_credit_cycle_allocation(db, user, "starter", now=user.lastCreditResetAt)
    update_plan("starter", {"projectLimit": 5, "keywordLimit": 10, "manualRefreshLimit": 9,
                            "keywordResearchLimit": 9, "competitorSpyLimit": 9}, db, admin)
    project = Project(id="p", name="P", domain="example.com", userId=user.id); db.add(project)
    db.add(Keyword(id="k", projectId=project.id, userId=user.id, keyword="one")); db.commit()
    with pytest.raises(ApiError): ensure_project_limit(db, user.id)
    with pytest.raises(ApiError): ensure_keyword_limit(db, user.id)
    assert get_feature_usage(db, user.id, "manual_refresh")["limit"] == 2
    assert get_feature_usage(db, user.id, "keyword_research")["limit"] == 3
    assert get_feature_usage(db, user.id, "competitor_spy")["limit"] == 4


def test_pending_boundary_uses_destination_offering_and_legacy_backfill_uses_old_defaults():
    db = make_db(); admin = make_user(db, "admin", admin=True)
    legacy = make_user(db, "legacy")
    update_plan("starter", {"keywordLimit": 175}, db, admin)
    assert active_entitlements(db, legacy)["keywordLimit"] == 100  # pre-Phase-20 effective value

    user = make_user(db, "upgrade")
    apply_credit_cycle_allocation(db, user, "starter", now=user.lastCreditResetAt)
    update_plan("pro", {"keywordLimit": 650, "monthlyCredits": 42000, "automaticCredits": 26000}, db, admin)
    user.pendingPlanChange = "pro"; user.lastCreditResetAt = datetime.utcnow() - timedelta(days=31); db.commit()
    assert active_entitlements(db, user)["keywordLimit"] == 175
    assert reset_monthly_credits(db, user)["plan"] == "pro"
    assert active_entitlements(db, user)["keywordLimit"] == 650
    assert (user.planCreditBalance, user.automaticCreditBalance) == (16000, 26000)


def test_pending_downgrade_and_expiry_to_free_use_boundary_offerings_without_deleting_data():
    db = make_db(); admin = make_user(db, "admin", admin=True)
    downgrade = make_user(db, "downgrade", "pro")
    apply_credit_cycle_allocation(db, downgrade, "pro", now=downgrade.lastCreditResetAt)
    update_plan("starter", {"keywordLimit": 80}, db, admin)
    downgrade.pendingPlanChange = "starter"; downgrade.lastCreditResetAt = datetime.utcnow() - timedelta(days=31); db.commit()
    assert active_entitlements(db, downgrade)["keywordLimit"] == 500
    reset_monthly_credits(db, downgrade)
    assert active_entitlements(db, downgrade)["keywordLimit"] == 80

    expiring = make_user(db, "expiring", "starter")
    project = Project(id="preserved-project", name="P", domain="keep.example.com", userId=expiring.id)
    keyword = Keyword(id="preserved-keyword", projectId=project.id, userId=expiring.id, keyword="keep")
    subscription = Subscription(userId=expiring.id, planId=0, status="past_due", isActive=True,
                                startDate=datetime.utcnow() - timedelta(days=40), endDate=datetime.utcnow() - timedelta(days=8))
    expiring.subscriptionStatus = "past_due"; db.add_all([project, keyword, subscription]); db.commit()
    update_plan("free_trial", {"keywordLimit": 7, "monthlyCredits": 120}, db, admin)
    handle_grace_period_expiry(db, expiring)
    assert active_entitlements(db, expiring)["keywordLimit"] == 7
    assert expiring.creditBalance == 120
    assert db.get(Project, project.id) and db.get(Keyword, keyword.id)


def test_new_free_registration_uses_current_admin_offering_snapshot():
    db = make_db(); admin = make_user(db, "admin", admin=True)
    update_plan("free_trial", {"projectLimit": 2, "keywordLimit": 8,
                               "monthlyCredits": 140, "automaticCredits": 20}, db, admin)

    class NoopThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    with patch("app.services.auth_service.threading.Thread", NoopThread):
        result = register_user(db, {
            "name": "New Free",
            "email": "new-free@example.com",
            "mobile": "+919876540001",
            "password": "StrongPassword123!",
        })

    user = db.get(User, result["id"])
    entitlements = active_entitlements(db, user)
    assert (entitlements["domain_limit"], entitlements["keywordLimit"]) == (2, 8)
    assert (entitlements["monthlyCredits"], entitlements["automaticCredits"]) == (140, 20)
    assert (user.planCreditBalance, user.automaticCreditBalance, user.creditBalance) == (120, 20, 120)
    assert db.scalar(select(func.count()).select_from(SubscriptionEntitlementSnapshot).where(
        SubscriptionEntitlementSnapshot.userId == user.id
    )) == 1
