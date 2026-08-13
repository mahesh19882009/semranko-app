import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Subscription, Project, Keyword, CreditLedger
from app.services.plan_service import (
    PLAN_DEFINITIONS,
    get_effective_plan_key,
    should_reset_credits,
    reset_monthly_credits,
    reset_due_credits_for_all_users,
    activate_paid_plan,
    change_user_plan,
    reactivate_subscription,
)
from app.services.payment_service import get_plan_by_id, activate_subscription
from app.services.credit_service import deduct_credits, refund_credits
from app.core.errors import ApiError


def make_user(db: Session, user_id="user-1", email=None, plan="free_trial", credit_balance=0.0, subscription_status="trialing", plan_anniversary_at=None, last_credit_reset_at=None):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Test User",
        email=email or f"{user_id}@test.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        createdAt=now,
        updatedAt=now,
    )
    user.planAnniversaryAt = plan_anniversary_at if plan_anniversary_at is not None else now
    user.lastCreditResetAt = last_credit_reset_at if last_credit_reset_at is not None else now
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestMonthlyCreditRefresh:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    def test_first_monthly_refresh_when_due(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 1
        assert ledgers[0].actionType == "monthly_refresh"
        assert ledgers[0].amount == 8000.0
        assert ledgers[0].balanceBefore == 500.0
        assert ledgers[0].balanceAfter == 3000.0
        assert ledgers[0].planName == "Starter"

    def test_refresh_before_due(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now + timedelta(days=1),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is False
        assert user.creditBalance == 500.0
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 0

    def test_exact_due_boundary(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=30),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0

    def test_refresh_after_due(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=35),
            last_credit_reset_at=self.now - timedelta(days=36),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0

    def test_second_monthly_cycle(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=6000.0,
            plan_anniversary_at=self.now - timedelta(days=60),
            last_credit_reset_at=self.now - timedelta(days=30),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 1

    def test_duplicate_scheduler_execution(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        result1 = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        result2 = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result1["reset"] is True
        assert result2["reset"] is False
        assert user.creditBalance == 3000.0
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 1

    def test_active_user_gets_refresh(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=0.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0

    def test_trial_user_no_refresh(self):
        user = make_user(
            self.db,
            plan="free_trial",
            subscription_status="trialing",
            credit_balance=50.0,
            plan_anniversary_at=self.now - timedelta(days=30),
        )
        
        result = reset_due_credits_for_all_users(self.db)
        
        assert result["reset_count"] == 0
        self.db.refresh(user)
        assert user.creditBalance == 50.0

    def test_past_due_user_no_refresh(self):
        user = make_user(
            self.db,
            plan="starter",
            subscription_status="past_due",
            credit_balance=100.0,
            plan_anniversary_at=self.now - timedelta(days=30),
        )
        
        result = reset_due_credits_for_all_users(self.db)
        
        assert result["reset_count"] == 0
        self.db.refresh(user)
        assert user.creditBalance == 100.0

    def test_grace_period_user_no_refresh(self):
        user = make_user(
            self.db,
            plan="free_trial",
            subscription_status="trialing",
            credit_balance=50.0,
            plan_anniversary_at=self.now - timedelta(days=10),
        )
        
        result = reset_due_credits_for_all_users(self.db)
        
        assert result["reset_count"] == 0
        self.db.refresh(user)
        assert user.creditBalance == 50.0

    def test_inactive_user_no_refresh(self):
        user = make_user(
            self.db,
            plan="starter",
            subscription_status="inactive",
            credit_balance=100.0,
            plan_anniversary_at=self.now - timedelta(days=30),
        )
        
        result = reset_due_credits_for_all_users(self.db)
        
        assert result["reset_count"] == 0
        self.db.refresh(user)
        assert user.creditBalance == 100.0

    def test_zero_balance_receives_monthly_credits(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=0.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0

    def test_existing_balance_is_replaced(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=1234.5,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0

    def test_previous_unused_credits_do_not_roll_over(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=5000.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        result = reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert result["reset"] is True
        assert user.creditBalance == 3000.0
        assert user.creditBalance != 5000.0 + 3000.0

    def test_monthly_refresh_creates_exactly_one_ledger_entry(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        ledgers = self.db.scalars(select(CreditLedger).where(CreditLedger.userId == user.id)).all()
        assert len(ledgers) == 1

    def test_ledger_contains_correct_before_after_balance(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=2500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        ledger = self.db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert ledger.balanceBefore == 2500.0
        assert ledger.balanceAfter == 3000.0

    def test_ledger_contains_correct_plan_and_amount(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="pro",
            subscription_status="active",
            credit_balance=100.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=31),
        )
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        ledger = self.db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert ledger.planName == "Pro"
        assert ledger.amount == 40000.0
        assert ledger.netCreditChange == 39900.0

    def test_upgrade_then_refresh_uses_new_plan_credits(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=6000.0,
            plan_anniversary_at=self.now - timedelta(days=60),
            last_credit_reset_at=self.now - timedelta(days=30),
        )
        
        change_user_plan(self.db, user.id, "pro")
        self.db.refresh(user)
        
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange == "pro"
        assert user.creditBalance == 6000.0
        
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        self.db.commit()
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange is None
        assert user.creditBalance == 15000.0

    def test_downgrade_then_refresh_uses_downgraded_plan_credits(self):
        user = make_user(
            self.db,
            user_id="user-pro",
            plan="pro",
            subscription_status="active",
            credit_balance=30000.0,
            plan_anniversary_at=self.now - timedelta(days=60),
            last_credit_reset_at=self.now - timedelta(days=30),
        )
        
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(10):
            kw = Keyword(id=f"k{i}", projectId=project.id, userId=user.id, keyword=f"test{i}", isActive=True)
            self.db.add(kw)
        self.db.commit()
        
        change_user_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange == "starter"
        assert user.creditBalance == 30000.0
        
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        self.db.commit()
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange is None
        assert user.creditBalance == 3000.0

    def test_reactivation_then_refresh_uses_current_plan_credits(self):
        user = make_user(
            self.db,
            user_id="user-inactive",
            plan="starter",
            subscription_status="inactive",
            credit_balance=0.0,
            plan_anniversary_at=self.now - timedelta(days=60),
            last_credit_reset_at=self.now - timedelta(days=30),
        )
        
        reactivate_subscription(self.db, user.id, "starter")
        self.db.refresh(user)
        
        assert user.subscriptionStatus == "active"
        assert user.creditBalance == 3000.0
        
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        self.db.commit()
        
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert user.creditBalance == 3000.0

    def test_same_plan_cycle_replaces_expiring_plan_credits(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=60),
        )
        
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        self.db.commit()
        reset_monthly_credits(self.db, user)
        self.db.refresh(user)
        
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0

    def test_credit_deduction_behavior_unchanged(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=100.0,
        )
        
        deduct_credits(self.db, user.id, 20.0, "charge", "Test deduction")
        self.db.refresh(user)
        
        assert user.creditBalance == 80.0

    def test_credit_refund_behavior_unchanged(self):
        user = make_user(
            self.db,
            plan="starter",
            subscription_status="active",
            credit_balance=80.0,
        )
        
        refund_credits(self.db, user.id, 20.0, "Test refund")
        self.db.refresh(user)
        
        assert user.creditBalance == 100.0

    def test_no_dataforseo_calls_triggered(self):
        user = make_user(
            self.db,
            user_id="user-active",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
        )
        
        async_tasks_before = self.db.scalar(select(func.count()).select_from(Keyword))
        
        reset_monthly_credits(self.db, user)
        self.db.commit()
        
        async_tasks_after = self.db.scalar(select(func.count()).select_from(Keyword))
        
        assert async_tasks_before == async_tasks_after

    def test_account_wide_keyword_limit_unchanged(self):
        from app.services.keyword_service import add_keyword
        
        user = make_user(
            self.db,
            plan="free_trial",
            subscription_status="trialing",
            credit_balance=100.0,
        )
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()
        
        for i in range(5):
            add_keyword(self.db, user.id, project.id, {"keyword": f"kw{i}"})
        
        with pytest.raises(ApiError) as exc_info:
            add_keyword(self.db, user.id, project.id, {"keyword": "overflow"})
        assert "Keyword limit reached" in str(exc_info.value)

    def test_reset_due_credits_batch_skips_non_active(self):
        user_active = make_user(
            self.db,
            user_id="user-active",
            email="active@test.com",
            plan="starter",
            subscription_status="active",
            credit_balance=500.0,
            plan_anniversary_at=self.now - timedelta(days=30),
            last_credit_reset_at=self.now - timedelta(days=30),
        )
        user_trial = make_user(
            self.db,
            user_id="user-trial",
            email="trial@test.com",
            plan="free_trial",
            subscription_status="trialing",
            credit_balance=50.0,
            plan_anniversary_at=self.now - timedelta(days=30),
        )
        user_inactive = make_user(
            self.db,
            user_id="user-inactive",
            email="inactive@test.com",
            plan="starter",
            subscription_status="inactive",
            credit_balance=100.0,
            plan_anniversary_at=self.now - timedelta(days=30),
        )
        
        result = reset_due_credits_for_all_users(self.db)
        
        assert result["reset_count"] == 1
        assert result["skipped_count"] == 1
        
        self.db.refresh(user_active)
        self.db.refresh(user_trial)
        self.db.refresh(user_inactive)
        
        assert user_active.creditBalance == 3000.0
        assert user_trial.creditBalance == 50.0
        assert user_inactive.creditBalance == 100.0
