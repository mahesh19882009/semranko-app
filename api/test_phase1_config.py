import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Subscription, Project, Keyword, CreditLedger
from app.core.config import settings
from app.services.plan_service import (
    PLAN_DEFINITIONS,
    get_plan_monthly_credits,
    list_available_plans,
    get_user_plan_limits,
    get_user_plan_limits_from_plan,
)
from app.services.credit_service import (
    get_credit_balance,
    deduct_credits,
    refund_credits,
    add_purchased_credits,
    reserve_credits,
    consume_reserved,
    refund_reserved,
)
from app.api.routes.marketing import MARKETING_FAQS


def make_user(db: Session, plan="pro", credit_balance=0.0):
    now = datetime.utcnow()
    user = User(
        id="user-1",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus="active",
        createdAt=now,
        updatedAt=now,
        emailVerificationExpiresAt=now,
        passwordResetExpiresAt=now,
        trialStartsAt=now,
        trialEndsAt=now,
        planAnniversaryAt=now,
        lastCreditResetAt=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestPlanConfig:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_all_plans_exist(self):
        assert "free_trial" in settings.plan_config.plans
        assert "starter" in settings.plan_config.plans
        assert "pro" in settings.plan_config.plans
        assert "agency" in settings.plan_config.plans
        assert "enterprise" in settings.plan_config.plans

    def test_new_user_model_defaults_to_permanent_free(self):
        user = User(
            id="default-free-user", name="Free", email="default-free@example.com",
            passwordHash="hash",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        assert user.selectedPlan == "free_trial"
        assert user.subscriptionStatus == "free"

    def test_refresh_frequency_is_paid_monthly_and_disabled_for_free(self):
        assert settings.plan_config.plans["free_trial"].refresh_frequency == "none"
        for key in ("starter", "pro", "agency", "enterprise"):
            assert settings.plan_config.plans[key].refresh_frequency == "monthly"

    def test_existing_values_preserved(self):
        starter = settings.plan_config.plans["starter"]
        assert starter.monthly_price_inr == 999
        assert starter.yearly_price_inr == 10789
        assert starter.domain_limit == 1
        assert starter.keyword_limit == 100
        assert starter.monthly_credits == 8000
        assert starter.automatic_credits == 5000
        assert starter.competitors_per_project == 3
        assert starter.reports_per_month == 5

        pro = settings.plan_config.plans["pro"]
        assert pro.monthly_price_inr == 3999
        assert pro.monthly_credits == 40000
        assert pro.automatic_credits == 25000
        assert pro.keyword_limit == 500

    def test_credit_costs_centralized(self):
        assert settings.plan_config.credit_costs["add_keyword"] == 20
        assert settings.plan_config.credit_costs["weekly_refresh_per_keyword"] == 10
        assert settings.plan_config.credit_costs["monthly_refresh_per_keyword"] == 10
        assert settings.plan_config.credit_costs["keyword_research"] == 20
        assert settings.plan_config.credit_costs["manual_refresh_per_keyword"] == 20
        assert settings.plan_config.credit_costs["competitor_spy"] == 30
        assert settings.plan_config.credit_costs["extra_project"] == 10
        assert settings.plan_config.credit_costs["tracked_keyword"] == 20
        assert settings.plan_config.credit_costs["download_report"] == 10
        assert settings.plan_config.credit_costs["bulk_add_keyword"] == 20

    def test_dataforseo_costs_separate(self):
        assert settings.plan_config.dataforseo_costs["serp_live_advanced"] == 0.024
        assert settings.plan_config.dataforseo_costs["labs_keyword_overview"] == 0.013
        assert settings.plan_config.dataforseo_costs["serp_async_task"] == 0.012
        assert len(settings.plan_config.dataforseo_costs) == 9

    def test_top_up_config_unchanged(self):
        top_up = settings.plan_config.top_up
        assert top_up.credits_per_100_inr == 600
        assert top_up.base_price_inr == 100
        assert top_up.min_multiplier == 1
        assert top_up.no_bulk_discount is True

    def test_backward_compatible_aliases(self):
        from app.core.config import (
            USER_CREDIT_COSTS,
            DATAFORSEO_CREDIT_COSTS,
            PLAN_KEYWORD_LIMITS,
            PLAN_MONTHLY_CREDITS,
            PLAN_COMPETITOR_SPY_LIMITS,
            CREDIT_TOP_UP_CONFIG,
            CONVERSION_RATE_USD_TO_INR,
            CONVERSION_FEE_PCT,
            GST_RATE,
            TRIAL_DAYS,
        )
        assert USER_CREDIT_COSTS["add_keyword"] == 20
        assert DATAFORSEO_CREDIT_COSTS["serp_live_advanced"] == 0.024
        assert PLAN_KEYWORD_LIMITS["starter"] == 100
        assert PLAN_MONTHLY_CREDITS["pro"] == 40000
        assert PLAN_COMPETITOR_SPY_LIMITS["agency"] == 25
        assert CREDIT_TOP_UP_CONFIG["credits_per_100_inr"] == 600
        assert CONVERSION_RATE_USD_TO_INR == 95.23
        assert CONVERSION_FEE_PCT == 3.0
        assert GST_RATE == 0.18
        assert TRIAL_DAYS == 0

    def test_plan_definitions_backward_compatible(self):
        assert PLAN_DEFINITIONS["free_trial"]["name"] == "Free"
        assert PLAN_DEFINITIONS["free_trial"]["refreshFrequency"] == "none"
        assert PLAN_DEFINITIONS["free_trial"]["limits"]["weeklyTrackingEnabled"] is False
        assert PLAN_DEFINITIONS["free_trial"]["limits"]["automaticCredits"] == 0
        assert PLAN_DEFINITIONS["starter"]["monthlyCredits"] == 8000
        assert PLAN_DEFINITIONS["starter"]["automaticCredits"] == 5000
        assert PLAN_DEFINITIONS["starter"]["spendableCredits"] == 3000
        assert PLAN_DEFINITIONS["starter"]["keywordLimit"] == 100
        assert PLAN_DEFINITIONS["pro"]["refreshFrequency"] == "monthly"
        assert "limits" in PLAN_DEFINITIONS["pro"]

    def test_list_available_plans(self):
        plans = list_available_plans()
        assert len(plans) == 5
        starter = next(p for p in plans if p["key"] == "starter")
        assert starter["refreshFrequency"] == "monthly"
        assert starter["limits"]["monthlyCredits"] == 8000
        assert starter["limits"]["automaticCredits"] == 5000
        assert starter["limits"]["spendableCredits"] == 3000
        free = next(p for p in plans if p["key"] == "free_trial")
        assert free["refreshFrequency"] == "none"
        assert free["limits"]["manualRefreshLimit"] == 0
        assert free["limits"]["keywordResearchLimit"] == 0
        assert free["limits"]["competitorSpyLimit"] == 0

    def test_pricing_faqs_match_credit_and_permanent_free_policy(self):
        answers = " ".join(item["a"] for item in MARKETING_FAQS).lower()
        assert "no hidden keyword limits" not in answers
        assert "free trial" not in answers
        assert "purchased top-up credits remain separate" in answers


class TestCreditReservation:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = make_user(self.db, plan="pro", credit_balance=100.0)

    def teardown_method(self):
        self.db.close()

    def test_reserve_sufficient_balance(self):
        balance = reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-001",
        )
        assert balance == 70.0

    def test_reserve_insufficient_balance(self):
        with pytest.raises(Exception):
            reserve_credits(
                self.db,
                self.user.id,
                150.0,
                "test_reserve",
                "Test reservation",
                reference="test-002",
            )

    def test_reserve_idempotent(self):
        balance1 = reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-003",
        )
        balance2 = reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-003",
        )
        assert balance1 == balance2 == 70.0

    def test_consume_reserved(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-004",
        )
        balance = consume_reserved(
            self.db,
            self.user.id,
            reference="test-004",
            amount=20.0,
            action_type="charge",
            description="Test consume",
        )
        assert balance == 70.0

    def test_consume_more_than_reserved(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-005",
        )
        balance = consume_reserved(
            self.db,
            self.user.id,
            reference="test-005",
            amount=50.0,
            action_type="charge",
            description="Test consume",
        )
        assert balance == 70.0

    def test_refund_reserved(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-006",
        )
        balance = refund_reserved(
            self.db,
            self.user.id,
            reference="test-006",
            amount=10.0,
            description="Test refund",
        )
        assert balance == 80.0

    def test_partial_consume_and_refund(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-007",
        )
        consume_reserved(
            self.db,
            self.user.id,
            reference="test-007",
            amount=20.0,
            action_type="charge",
            description="Partial consume",
        )
        balance = refund_reserved(
            self.db,
            self.user.id,
            reference="test-007",
            amount=10.0,
            description="Partial refund",
        )
        assert balance == 80.0

    def test_duplicate_consume_idempotent(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-008",
        )
        consume_reserved(
            self.db,
            self.user.id,
            reference="test-008",
            amount=30.0,
            action_type="charge",
            description="Full consume",
        )
        with pytest.raises(Exception):
            consume_reserved(
                self.db,
                self.user.id,
                reference="test-008",
                amount=10.0,
                action_type="charge",
                description="Duplicate consume",
            )

    def test_duplicate_refund_idempotent(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-009",
        )
        balance1 = refund_reserved(
            self.db,
            self.user.id,
            reference="test-009",
            amount=30.0,
            description="Full refund",
        )
        balance2 = refund_reserved(
            self.db,
            self.user.id,
            reference="test-009",
            amount=10.0,
            description="Duplicate refund",
        )
        assert balance1 == balance2 == 100.0

    def test_cannot_refund_more_than_reserved(self):
        reserve_credits(
            self.db,
            self.user.id,
            30.0,
            "test_reserve",
            "Test reservation",
            reference="test-010",
        )
        consume_reserved(
            self.db,
            self.user.id,
            reference="test-010",
            amount=20.0,
            action_type="charge",
            description="Partial consume",
        )
        balance = refund_reserved(
            self.db,
            self.user.id,
            reference="test-010",
            amount=20.0,
            description="Over refund",
        )
        assert balance == 80.0


class TestPurchaseLedger:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = make_user(self.db, plan="pro", credit_balance=50.0)

    def teardown_method(self):
        self.db.close()

    def test_add_purchased_credits_populates_all_fields(self):
        balance = add_purchased_credits(
            self.db,
            self.user.id,
            100.0,
            "Test purchase",
            "order_test_123",
        )
        assert balance == 150.0

        ledger = self.db.scalar(
            select(CreditLedger).where(CreditLedger.userId == self.user.id)
        )
        assert ledger is not None
        assert ledger.actionType == "purchase"
        assert float(ledger.amount) == 100.0
        assert float(ledger.creditsReserved) == 0.0
        assert float(ledger.creditsConsumed) == 100.0
        assert float(ledger.creditsRefunded) == 0.0
        assert float(ledger.netCreditChange) == 100.0
        assert float(ledger.balanceBefore) == 50.0
        assert float(ledger.balanceAfter) == 150.0
        assert ledger.projectId is None
        assert ledger.keywordId is None
        assert ledger.taskId is None
        assert ledger.requestId is None
        assert ledger.relatedOrderId == "order_test_123"
        assert ledger.status == "completed"


class TestProjectCreationFree:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = make_user(self.db, plan="pro", credit_balance=100.0)

    def teardown_method(self):
        self.db.close()

    def test_project_creation_does_not_deduct_credits(self):
        from app.services.project_service import create_project
        balance_before = get_credit_balance(self.db, self.user.id)
        project = create_project(self.db, self.user.id, {"name": "Test Project", "domain": "test.com"})
        balance_after = get_credit_balance(self.db, self.user.id)
        assert balance_after == balance_before
        assert project is not None
