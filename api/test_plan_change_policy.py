import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from unittest.mock import patch

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Subscription, Project, Keyword, CreditLedger, PaymentOrder
from app.services.plan_service import (
    PLAN_DEFINITIONS,
    change_user_plan,
    reset_monthly_credits,
    reset_due_credits_for_all_users,
    validate_plan_change,
    get_effective_plan_key,
)
from app.services.payment_service import activate_subscription, verify_payment_signature
from app.core.errors import ApiError


def make_user(db: Session, user_id="user-1", plan="starter", credit_balance=0.0, subscription_status="active", plan_anniversary_at=None, last_credit_reset_at=None):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Test User",
        email=f"{user_id}@test.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        planAnniversaryAt=plan_anniversary_at if plan_anniversary_at is not None else now,
        lastCreditResetAt=last_credit_reset_at if last_credit_reset_at is not None else now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestUpgradeBecomesPending:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_normal_upgrade_sets_pending(self):
        user = make_user(self.db, user_id="u1", plan="starter", credit_balance=6000.0)
        result = change_user_plan(self.db, user.id, "pro")
        assert result.selectedPlan == "starter"
        assert result.pendingPlanChange == "pro"
        assert result.creditBalance == 6000.0

    def test_upgrade_does_not_change_subscription(self):
        user = make_user(self.db, user_id="u2", plan="starter")
        sub = Subscription(userId=user.id, planId=0, status="active", isActive=True, startDate=datetime.utcnow(), endDate=datetime.utcnow() + timedelta(days=30))
        self.db.add(sub)
        self.db.commit()
        
        change_user_plan(self.db, user.id, "pro")
        self.db.refresh(sub)
        assert sub.planId == 0

    def test_repeated_upgrade_overwrites_pending(self):
        user = make_user(self.db, user_id="u3", plan="starter")
        change_user_plan(self.db, user.id, "pro")
        change_user_plan(self.db, user.id, "agency")
        self.db.refresh(user)
        assert user.pendingPlanChange == "agency"


class TestDowngradeBecomesPending:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_normal_downgrade_sets_pending(self):
        user = make_user(self.db, user_id="u4", plan="pro", credit_balance=30000.0)
        result = change_user_plan(self.db, user.id, "starter")
        assert result.selectedPlan == "pro"
        assert result.pendingPlanChange == "starter"
        assert result.creditBalance == 30000.0

    def test_downgrade_blocked_by_usage(self):
        user = make_user(self.db, user_id="u5", plan="pro")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(101):
            kw = Keyword(id=f"k{i}", projectId=project.id, userId=user.id, keyword=f"test{i}", isActive=True)
            self.db.add(kw)
        self.db.commit()
        
        with pytest.raises(ApiError):
            change_user_plan(self.db, user.id, "starter")


class TestCurrentPlanRemainsActive:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_credits_retained_before_boundary(self):
        user = make_user(self.db, user_id="u6", plan="pro", credit_balance=30000.0)
        change_user_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.creditBalance == 30000.0
        assert user.selectedPlan == "pro"

    def test_usage_limits_based_on_current_plan(self):
        user = make_user(self.db, user_id="u7", plan="pro")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(101):
            kw = Keyword(id=f"k{i}", projectId=project.id, userId=user.id, keyword=f"test{i}", isActive=True)
            self.db.add(kw)
        self.db.commit()
        
        limits = validate_plan_change(self.db, user, "starter")
        assert limits["allowed"] is False


class TestPendingUpgradeActivatesAtBoundary:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_pending_upgrade_applies_at_reset(self):
        user = make_user(
            self.db,
            user_id="u8",
            plan="starter",
            credit_balance=6000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        change_user_plan(self.db, user.id, "pro")
        assert user.pendingPlanChange == "pro"
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange is None
        assert user.creditBalance == 15000.0
        assert user.automaticCreditBalance == 25000.0


class TestPendingDowngradeActivatesAtBoundary:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_pending_downgrade_applies_at_reset(self):
        user = make_user(
            self.db,
            user_id="u9",
            plan="pro",
            credit_balance=30000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        change_user_plan(self.db, user.id, "starter")
        assert user.pendingPlanChange == "starter"
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange is None
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0


class TestExistingCreditsRetained:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_credits_not_removed_on_pending_downgrade(self):
        user = make_user(self.db, user_id="u10", plan="pro", credit_balance=30000.0)
        change_user_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.creditBalance == 30000.0

    def test_credits_not_granted_on_pending_upgrade(self):
        user = make_user(self.db, user_id="u11", plan="starter", credit_balance=6000.0)
        change_user_plan(self.db, user.id, "pro")
        self.db.refresh(user)
        assert user.creditBalance == 6000.0


class TestCreditsResetCorrectly:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_credits_reset_to_new_plan_at_boundary(self):
        user = make_user(
            self.db,
            user_id="u12",
            plan="starter",
            credit_balance=5000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        change_user_plan(self.db, user.id, "pro")
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        assert user.creditBalance == 15000.0
        assert user.automaticCreditBalance == 25000.0

    def test_ledger_reflects_actual_balance(self):
        user = make_user(
            self.db,
            user_id="u13",
            plan="starter",
            credit_balance=5000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        change_user_plan(self.db, user.id, "pro")
        reset_monthly_credits(self.db, user)
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 1
        assert ledgers[0].amount == 40000.0
        assert ledgers[0].balanceBefore == 5000.0
        assert ledgers[0].balanceAfter == 15000.0
        assert ledgers[0].automaticCreditsChange == 25000.0


class TestBatchAndSingleResetConsistent:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_batch_reset_applies_pending_plan(self):
        user = make_user(
            self.db,
            user_id="u14",
            plan="pro",
            credit_balance=30000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        change_user_plan(self.db, user.id, "starter")
        
        reset_due_credits_for_all_users(self.db)
        self.db.refresh(user)
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange is None
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0


class TestPaymentPlanValidation:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_payment_mismatch_rejects_activation(self):
        user = make_user(self.db, user_id="u15", plan="pro", credit_balance=30000.0)
        change_user_plan(self.db, user.id, "starter")
        
        with pytest.raises(Exception, match="Payment plan mismatch"):
            activate_subscription(
                db=self.db,
                user_id=user.id,
                plan_id=1,
                payment_id="pay_test",
                order_id="order_test"
            )
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange == "starter"

    def test_payment_matching_pending_plan_clears_pending(self):
        user = make_user(self.db, user_id="u16", plan="starter", credit_balance=6000.0)
        change_user_plan(self.db, user.id, "pro")
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange is None

    def test_payment_without_pending_plan_activates_normally(self):
        user = make_user(self.db, user_id="u17", plan="starter", credit_balance=6000.0)
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange is None


class TestPaymentFailure:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_failed_payment_leaves_state_unchanged(self):
        user = make_user(self.db, user_id="u18", plan="starter", credit_balance=6000.0)
        change_user_plan(self.db, user.id, "pro")
        
        with pytest.raises(Exception):
            activate_subscription(
                db=self.db,
                user_id=user.id,
                plan_id=999,
                payment_id="pay_test",
                order_id="order_test"
            )
        self.db.refresh(user)
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange == "pro"
        assert user.creditBalance == 6000.0


class TestRepeatedPendingPlanChanges:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_latest_pending_plan_wins(self):
        user = make_user(self.db, user_id="u19", plan="starter", credit_balance=6000.0)
        change_user_plan(self.db, user.id, "pro")
        change_user_plan(self.db, user.id, "agency")
        self.db.refresh(user)
        assert user.pendingPlanChange == "agency"
        assert user.creditBalance == 6000.0

    def test_no_duplicate_ledger_entries(self):
        user = make_user(self.db, user_id="u20", plan="starter")
        change_user_plan(self.db, user.id, "pro")
        change_user_plan(self.db, user.id, "agency")
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 0


class TestInvalidPendingPlan:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_invalid_pending_plan_is_ignored_at_boundary(self):
        user = make_user(
            self.db,
            user_id="u21",
            plan="starter",
            credit_balance=6000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        user.pendingPlanChange = "invalid_plan"
        self.db.add(user)
        self.db.commit()
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange is None
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0


class TestIdempotency:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_duplicate_payment_does_not_double_credit(self):
        user = make_user(self.db, user_id="u22", plan="starter", credit_balance=6000.0)
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        balance_after_first = user.creditBalance
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        assert user.creditBalance == balance_after_first
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len([l for l in ledgers if l.actionType == "purchase"]) == 1

    def test_duplicate_payment_does_not_change_anniversary(self):
        user = make_user(self.db, user_id="u23", plan="starter", credit_balance=6000.0)
        original_anniversary = user.planAnniversaryAt
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        first_anniversary = user.planAnniversaryAt
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        assert user.planAnniversaryAt == first_anniversary


class TestPendingPlanClearedAtBoundary:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_pending_plan_cleared_after_successful_transition(self):
        user = make_user(
            self.db,
            user_id="u24",
            plan="starter",
            credit_balance=6000.0,
            plan_anniversary_at=datetime.utcnow() - timedelta(days=60),
            last_credit_reset_at=datetime.utcnow() - timedelta(days=30),
        )
        change_user_plan(self.db, user.id, "pro")
        assert user.pendingPlanChange == "pro"
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        assert user.pendingPlanChange is None
        assert user.selectedPlan == "pro"
