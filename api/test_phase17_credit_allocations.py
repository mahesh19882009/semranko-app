import json
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.core.config import get_settings
from app.db.models import Base, CreditLedger, Keyword, Project, RefreshJob, Subscription, User
from app.services.async_bulk_service import _paginate_eligible_keywords, _submit_weekly_refresh
from app.services.credit_service import (
    add_purchased_credits,
    deduct_automatic_credits,
    deduct_credits,
    reserve_automatic_credits,
)
from app.services.monthly_metrics_service import _paginate_eligible_keywords_for_monthly
from app.services.auth_service import register_user
from app.services.feature_usage_service import ensure_feature_available
from app.services.plan_service import (
    PLAN_DEFINITIONS,
    activate_paid_plan,
    apply_credit_cycle_allocation,
    build_usage_snapshot,
    change_user_plan,
    get_user_plan_limits,
    get_subscription_status,
    ensure_subscription_active,
    handle_grace_period_expiry,
    reset_monthly_credits,
)
from app.core.errors import ApiError


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db, user_id="user-1", plan="starter", status="active", spendable=0, automatic=0, purchased=0):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Credit Test",
        email=f"{user_id}@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        subscriptionStatus=status,
        creditBalance=spendable + purchased,
        planCreditBalance=spendable,
        purchasedCreditBalance=purchased,
        automaticCreditBalance=automatic,
        planAnniversaryAt=now,
        lastCreditResetAt=now,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    return user


@pytest.mark.parametrize(
    "plan,total,automatic,spendable,projects,keywords",
    [
        ("free_trial", 100, 0, 100, 1, 5),
        ("starter", 8000, 5000, 3000, 1, 100),
        ("pro", 40000, 25000, 15000, 5, 500),
        ("agency", 120000, 75000, 45000, 20, 1500),
    ],
)
def test_final_plan_allocations_and_limits(plan, total, automatic, spendable, projects, keywords):
    db = make_db()
    user = make_user(db, plan=plan, status="active")
    result = apply_credit_cycle_allocation(db, user, plan)
    db.refresh(user)

    assert PLAN_DEFINITIONS[plan]["monthlyCredits"] == total
    assert PLAN_DEFINITIONS[plan]["automaticCredits"] == automatic
    assert result == {
        "plan": plan,
        "total": float(total),
        "spendable": float(spendable),
        "purchased": 0.0,
        "automatic": float(automatic),
        "creditBalance": float(spendable),
    }
    assert user.planCreditBalance == spendable
    assert user.creditBalance == spendable
    assert user.automaticCreditBalance == automatic
    assert get_user_plan_limits(user)["domain_limit"] == projects
    assert get_user_plan_limits(user)["keywordLimit"] == keywords


def test_new_registration_receives_permanent_free_without_trial_expiry():
    db = make_db()

    class ImmediateNoopThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    with patch("app.services.auth_service.threading.Thread", ImmediateNoopThread):
        result = register_user(db, {
            "name": "Permanent Free",
            "email": "permanent-free@example.com",
            "mobile": "+919876543210",
            "password": "StrongPassword123!",
        })

    user = db.scalar(select(User).where(User.id == result["id"]))
    assert user.selectedPlan == "free_trial"
    assert user.subscriptionStatus == "free"
    assert user.trialStartsAt is None
    assert user.trialEndsAt is None
    assert user.creditBalance == 100
    assert user.planCreditBalance == 100
    assert user.automaticCreditBalance == 0


def test_historical_expired_trial_resolves_to_permanent_free_access():
    db = make_db()
    user = make_user(db, plan="free_trial", status="trialing", spendable=100)
    user.trialStartsAt = datetime.utcnow() - timedelta(days=40)
    user.trialEndsAt = datetime.utcnow() - timedelta(days=33)
    db.commit()

    assert get_subscription_status(user) == "free"
    ensure_subscription_active(user)
    assert get_user_plan_limits(user)["domain_limit"] == 1
    assert get_user_plan_limits(user)["keywordLimit"] == 5
    for feature in ("manual_refresh", "keyword_research", "competitor_spy"):
        with pytest.raises(ApiError) as error:
            ensure_feature_available(db, user.id, feature)
        assert error.value.data["error"] == "upgrade_required"


def test_free_is_never_scheduled_but_paid_active_keyword_is_scheduled():
    db = make_db()
    free = make_user(db, "free", "free_trial", "active", spendable=100)
    paid = make_user(db, "paid", "starter", "active", spendable=3000, automatic=5000)
    for user in (free, paid):
        project = Project(id=f"p-{user.id}", userId=user.id, name="P", domain=f"{user.id}.example.com")
        db.add(project)
        db.add(Keyword(id=f"k-{user.id}", projectId=project.id, userId=user.id, keyword=f"{user.id} kw", isActive=True))
    db.commit()

    weekly = [row for batch in _paginate_eligible_keywords(db, "weekly") for row in batch]
    monthly = [row for batch in _paginate_eligible_keywords_for_monthly(db) for row in batch]
    assert {row["keyword"] for row in weekly} == {"paid kw"}
    assert {row["keyword"] for row in monthly} == {"paid kw"}


def test_spendable_and_automatic_pools_cannot_cross_consume():
    db = make_db()
    user = make_user(db, spendable=0, automatic=100)

    with pytest.raises(HTTPException) as optional_error:
        deduct_credits(db, user.id, 20, "charge", "Optional operation")
    assert optional_error.value.status_code == 402
    db.refresh(user)
    assert user.automaticCreditBalance == 100

    deduct_automatic_credits(db, user.id, 10, "Weekly tracking", task_id="weekly-one")
    db.refresh(user)
    assert user.creditBalance == 0
    assert user.automaticCreditBalance == 90

    empty_auto = make_user(db, "empty-auto", spendable=100, automatic=0)
    with pytest.raises(HTTPException) as automatic_error:
        deduct_automatic_credits(db, empty_auto.id, 10, "Weekly tracking")
    assert automatic_error.value.status_code == 402
    db.refresh(empty_auto)
    assert empty_auto.creditBalance == 100


def test_cycle_reset_expires_plan_credits_preserves_purchased_and_is_idempotent():
    db = make_db()
    user = make_user(db, spendable=400, automatic=20, purchased=250)
    user.lastCreditResetAt = datetime.utcnow() - timedelta(days=31)
    user.planAnniversaryAt = user.lastCreditResetAt
    db.commit()

    first = reset_monthly_credits(db, user)
    second = reset_monthly_credits(db, user)
    db.refresh(user)
    assert first["reset"] is True
    assert second["reset"] is False
    assert user.planCreditBalance == 3000
    assert user.purchasedCreditBalance == 250
    assert user.creditBalance == 3250
    assert user.automaticCreditBalance == 5000
    allocations = db.scalars(select(CreditLedger).where(CreditLedger.actionType == "monthly_refresh")).all()
    assert len(allocations) == 1


def test_topups_are_separate_and_survive_cycle_reset():
    db = make_db()
    user = make_user(db, spendable=3000, automatic=5000)
    add_purchased_credits(db, user.id, 500, "Purchased credits", "topup-1")
    user.lastCreditResetAt = datetime.utcnow() - timedelta(days=31)
    db.commit()
    reset_monthly_credits(db, user)
    db.refresh(user)
    assert user.planCreditBalance == 3000
    assert user.purchasedCreditBalance == 500
    assert user.creditBalance == 3500
    assert user.automaticCreditBalance == 5000


def test_duplicate_topup_order_is_idempotent():
    db = make_db()
    user = make_user(db, spendable=3000, automatic=5000)
    add_purchased_credits(db, user.id, 500, "Purchased credits", "topup-duplicate")
    add_purchased_credits(db, user.id, 500, "Purchased credits retry", "topup-duplicate")
    db.refresh(user)
    assert user.purchasedCreditBalance == 500
    assert user.creditBalance == 3500
    purchases = db.scalars(select(CreditLedger).where(
        CreditLedger.relatedOrderId == "topup-duplicate",
        CreditLedger.creditPool == "purchased",
    )).all()
    assert len(purchases) == 1


def test_pending_plan_activates_once_with_new_plan_pools():
    db = make_db()
    user = make_user(db, spendable=3000, automatic=5000)
    change_user_plan(db, user.id, "pro")
    user.lastCreditResetAt = datetime.utcnow() - timedelta(days=31)
    db.commit()

    assert reset_monthly_credits(db, user)["reset"] is True
    assert reset_monthly_credits(db, user)["reset"] is False
    db.refresh(user)
    assert user.selectedPlan == "pro"
    assert user.pendingPlanChange is None
    assert user.planCreditBalance == 15000
    assert user.automaticCreditBalance == 25000


def test_free_to_paid_does_not_carry_free_allowance():
    db = make_db()
    user = make_user(db, plan="free_trial", status="active", spendable=100)
    activate_paid_plan(db, user.id, "starter")
    db.refresh(user)
    assert user.selectedPlan == "starter"
    assert user.planCreditBalance == 3000
    assert user.purchasedCreditBalance == 0
    assert user.creditBalance == 3000
    assert user.automaticCreditBalance == 5000


def test_paid_subscription_end_preserves_rows_and_stops_scheduling():
    db = make_db()
    user = make_user(db, plan="starter", status="past_due", spendable=100, automatic=100)
    project = Project(id="p-end", userId=user.id, name="P", domain="end.example.com")
    keyword = Keyword(id="k-end", projectId=project.id, userId=user.id, keyword="preserved", isActive=True)
    subscription = Subscription(
        id="sub-end", userId=user.id, planId=0, status="past_due", isActive=True,
        startDate=datetime.utcnow() - timedelta(days=40),
        endDate=datetime.utcnow() - timedelta(days=8),
    )
    db.add_all([project, keyword, subscription])
    db.commit()

    handle_grace_period_expiry(db, user)
    db.refresh(user)
    db.refresh(keyword)
    assert user.selectedPlan == "free_trial"
    assert user.subscriptionStatus == "free"
    assert user.creditBalance == 100
    assert user.automaticCreditBalance == 0
    assert keyword.isActive is True
    assert db.scalar(select(Keyword).where(Keyword.id == keyword.id)) is not None
    assert _paginate_eligible_keywords(db, "weekly") == []
    assert _paginate_eligible_keywords_for_monthly(db) == []


def test_insufficient_automatic_pool_blocks_dfs_submission():
    db = make_db()
    user = make_user(db, spendable=3000, automatic=0)
    project = Project(id="p-safe", userId=user.id, name="P", domain="safe.example.com")
    keyword = Keyword(id="k-safe", projectId=project.id, userId=user.id, keyword="safe kw", location="India", isActive=True)
    job = RefreshJob(
        id="job-safe", jobType="weekly_serp", status="processing", keywordCount=1,
        keywordsJson=json.dumps([{"keyword": "safe kw", "location": "India"}]),
    )
    db.add_all([project, keyword, job])
    db.commit()

    with patch("app.services.dataforseo_client._get_cached_serp", return_value=None), patch(
        "app.services.async_bulk_service.requests.post"
    ) as dfs:
        assert _submit_weekly_refresh(db, job, ["safe kw"]) is False
        dfs.assert_not_called()
    db.refresh(user)
    assert user.creditBalance == 3000
    assert user.automaticCreditBalance == 0


def test_partial_weekly_submission_refunds_unsubmitted_automatic_credits():
    db = make_db()
    user = make_user(db, spendable=0, automatic=2000)
    project = Project(id="p-partial", userId=user.id, name="P", domain="partial.example.com")
    db.add(project)
    keyword_texts = [f"partial-{index}" for index in range(101)]
    for index, keyword_text in enumerate(keyword_texts):
        db.add(Keyword(
            id=f"k-partial-{index}", projectId=project.id, userId=user.id,
            keyword=keyword_text, location="India", isActive=True,
        ))
    job = RefreshJob(
        id="job-partial", jobType="weekly_serp", status="processing", keywordCount=101,
        keywordsJson=json.dumps([{"keyword": keyword, "location": "India"} for keyword in keyword_texts]),
    )
    db.add(job)
    db.commit()

    first = type("Response", (), {
        "headers": {"Content-Type": "application/json"},
        "json": lambda self: {"tasks": [
            {"id": f"dfs-{index}", "data": {"keyword": keyword}}
            for index, keyword in enumerate(keyword_texts[:100])
        ]},
    })()
    second = type("Response", (), {
        "headers": {"Content-Type": "text/plain"},
        "text": "temporary failure",
    })()
    with patch("app.services.dataforseo_client._get_cached_serp", return_value=None), patch(
        "app.services.async_bulk_service.requests.post", side_effect=[first, second]
    ):
        assert _submit_weekly_refresh(db, job, keyword_texts) is True

    db.refresh(user)
    assert user.automaticCreditBalance == 1000
    reservation = db.scalar(select(CreditLedger).where(
        CreditLedger.userId == user.id,
        CreditLedger.creditPool == "automatic",
        CreditLedger.status == "pending",
    ))
    assert reservation.creditsReserved == 1010
    assert reservation.creditsRefunded == 10


def test_duplicate_automatic_scheduler_charge_is_idempotent_and_ledger_balances():
    db = make_db()
    user = make_user(db, spendable=0, automatic=50)
    deduct_automatic_credits(db, user.id, 10, "Weekly tracking", task_id="dfs-task-1")
    deduct_automatic_credits(db, user.id, 10, "Weekly tracking retry", task_id="dfs-task-1")
    db.refresh(user)
    rows = db.scalars(select(CreditLedger).where(CreditLedger.creditPool == "automatic")).all()
    assert len(rows) == 1
    assert user.automaticCreditBalance == 40
    assert rows[0].balanceBefore == 50
    assert rows[0].balanceAfter == 40
    assert rows[0].netCreditChange == -10


def test_frontend_snapshot_and_locked_feature_cost_configuration():
    db = make_db()
    user = make_user(db, spendable=3000, automatic=5000, purchased=250)
    snapshot = build_usage_snapshot(db, user)
    assert snapshot["plan"] == "starter"
    assert snapshot["totalMonthlyAllocation"] == 8000
    assert snapshot["spendableCreditsRemaining"] == 3250
    assert snapshot["purchasedCreditsRemaining"] == 250
    assert snapshot["automaticReservedAllocation"] == 5000
    assert snapshot["automaticReservedRemaining"] == 5000
    assert snapshot["nextCreditResetAt"] is not None
    assert snapshot["limits"]["manualRefreshLimit"] == 10
    assert snapshot["limits"]["keywordResearchLimit"] == 10
    assert snapshot["limits"]["competitorSpyLimit"] == 3
    assert snapshot["featureUsage"]["manualRefresh"]["limit"] == 10
    assert snapshot["featureUsage"]["keywordResearch"]["limit"] == 10
    assert snapshot["featureUsage"]["competitorSpy"]["limit"] == 3
    assert snapshot["creditCosts"] == {
        "addKeyword": 20,
        "bulkAddKeyword": 20,
        "manualRefresh": 20,
        "weeklyRefresh": 10,
        "monthlyMetrics": 10,
        "keywordResearch": 20,
        "competitorSpy": 30,
    }

    settings = get_settings()
    assert {key: settings.plan_config.credit_costs[key] for key in (
        "add_keyword",
        "bulk_add_keyword",
        "manual_refresh_per_keyword",
        "weekly_refresh_per_keyword",
        "monthly_refresh_per_keyword",
        "keyword_research",
        "competitor_spy",
    )} == {
        "add_keyword": 20,
        "bulk_add_keyword": 20,
        "manual_refresh_per_keyword": 20,
        "weekly_refresh_per_keyword": 10,
        "monthly_refresh_per_keyword": 10,
        "keyword_research": 20,
        "competitor_spy": 30,
    }
    assert {
        key: (
            plan["manualRefreshLimit"],
            plan["keywordResearchLimit"],
            plan["competitorSpyLimit"],
        )
        for key, plan in PLAN_DEFINITIONS.items()
        if key in {"free_trial", "starter", "pro", "agency"}
    } == {
        "free_trial": (0, 0, 0),
        "starter": (10, 10, 3),
        "pro": (50, 30, 10),
        "agency": (150, 75, 25),
    }
