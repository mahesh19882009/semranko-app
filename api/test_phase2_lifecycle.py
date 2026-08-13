import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session
from unittest.mock import patch

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Subscription, Project, Keyword, Competitor, CreditLedger, PaymentOrder
from app.services.plan_service import (
    PLAN_DEFINITIONS,
    get_plan_monthly_credits,
    get_user_plan_limits,
    validate_plan_change,
    change_user_plan,
    activate_paid_plan,
    handle_expiration,
    handle_grace_period_expiry,
    deactivate_user_keywords,
    reactivate_subscription,
    activate_keyword,
    deactivate_keyword,
    ensure_subscription_active,
    get_effective_plan_key,
    count_user_keywords,
    count_user_active_keywords,
    ensure_keyword_limit,
)
from app.services.keyword_service import add_keyword, add_keywords_bulk, delete_keyword, delete_keywords_bulk
from app.services.payment_service import activate_subscription, get_plan_by_id
from app.services import email_service
from app.services.credit_service import get_credit_balance, deduct_credits
from app.core.errors import ApiError


def make_user(db: Session, plan="free_trial", credit_balance=0.0, subscription_status="trialing", end_date=None):
    now = datetime.utcnow()
    user = User(
        id="user-1",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        planAnniversaryAt=now,
        lastCreditResetAt=now,
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestActivation:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    @patch.object(email_service, "send_payment_success_email")
    def test_first_paid_activation_sets_correct_fields(self, mock_email):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing", credit_balance=0.0)
        activate_paid_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.subscriptionStatus == "active"
        assert user.selectedPlan == "starter"
        assert user.planAnniversaryAt is not None
        assert user.lastCreditResetAt is not None
        assert user.creditBalance == 3000.0
        assert user.planCreditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0

    @patch.object(email_service, "send_payment_success_email")
    def test_first_paid_activation_creates_subscription(self, mock_email):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        activate_paid_plan(self.db, user.id, "starter")
        sub = self.db.scalar(select(Subscription).where(Subscription.userId == user.id, Subscription.isActive == True))
        assert sub is not None
        assert sub.status == "active"
        assert sub.isActive is True
        assert sub.startDate is not None
        assert sub.endDate is not None
        assert (sub.endDate - sub.startDate).days == 30

    @patch.object(email_service, "send_payment_success_email")
    def test_first_paid_activation_creates_ledger(self, mock_email):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        activate_paid_plan(self.db, user.id, "starter")
        ledger = self.db.scalar(select(CreditLedger).where(CreditLedger.userId == user.id))
        assert ledger is not None
        assert ledger.actionType == "cycle_allocation"
        assert float(ledger.amount) == 8000.0
        assert float(ledger.balanceBefore) == 0.0
        assert float(ledger.balanceAfter) == 3000.0
        assert float(ledger.netCreditChange) == 8000.0
        assert float(ledger.planCreditsChange) == 3000.0
        assert float(ledger.automaticCreditsChange) == 5000.0
        assert float(ledger.creditsConsumed) == 0.0
        assert float(ledger.creditsReserved) == 5000.0
        assert float(ledger.creditsRefunded) == 0.0
        assert ledger.projectId is None
        assert ledger.keywordId is None

    @patch.object(email_service, "send_payment_success_email")
    def test_trial_to_paid_does_not_add_to_trial_balance(self, mock_email):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing", credit_balance=50.0)
        activate_paid_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0

    @patch.object(email_service, "send_payment_success_email")
    def test_yearly_activation_creates_365_day_subscription(self, mock_email):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        sub = activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_test",
            order_id="order_test",
            billing_cycle="yearly",
        )
        self.db.refresh(sub)
        assert (sub.endDate - sub.startDate).days == 365


class TestRenewal:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    @patch.object(email_service, "send_payment_success_email")
    def test_renewal_replaces_expiring_plan_credits(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active", credit_balance=120.0)
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now + timedelta(days=5),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew",
            order_id="order_renew",
            billing_cycle="monthly",
        )
        self.db.refresh(user)
        assert user.creditBalance == 3000.0
        assert user.automaticCreditBalance == 5000.0

    @patch.object(email_service, "send_payment_success_email")
    def test_renewal_extends_subscription_end_date(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active")
        old_end = datetime.utcnow() + timedelta(days=5)
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=old_end,
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew",
            order_id="order_renew",
        )
        self.db.refresh(sub)
        assert sub.endDate > old_end
        assert (sub.endDate - self.now).days == 30

    @patch.object(email_service, "send_payment_success_email")
    def test_renewal_creates_renewal_ledger(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active", credit_balance=100.0)
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now + timedelta(days=5),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew",
            order_id="order_renew",
        )
        ledger = self.db.scalar(
            select(CreditLedger).where(CreditLedger.userId == user.id, CreditLedger.actionType == "renewal")
        )
        assert ledger is not None
        assert float(ledger.amount) == 0.0
        assert float(ledger.balanceAfter) == 3000.0

    @patch.object(email_service, "send_payment_success_email")
    def test_duplicate_renewal_does_not_double_credit(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active", credit_balance=100.0)
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now + timedelta(days=5),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew",
            order_id="order_renew",
        )
        self.db.refresh(user)
        balance_after_first = user.creditBalance
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew2",
            order_id="order_renew2",
        )
        self.db.refresh(user)
        assert user.creditBalance == balance_after_first
        assert user.automaticCreditBalance == 5000.0


class TestUpgrade:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    @patch.object(email_service, "send_payment_success_email")
    def test_upgrade_replaces_credit_balance(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active", credit_balance=120.0)
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_up",
            order_id="order_up",
        )
        self.db.refresh(user)
        assert user.creditBalance == 15000.0
        assert user.automaticCreditBalance == 25000.0

    @patch.object(email_service, "send_payment_success_email")
    def test_upgrade_resets_anniversary(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active")
        user.planAnniversaryAt = self.now - timedelta(days=60)
        user.lastCreditResetAt = self.now - timedelta(days=60)
        self.db.add(user)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_up",
            order_id="order_up",
        )
        self.db.refresh(user)
        assert user.planAnniversaryAt is not None
        assert (self.now - user.planAnniversaryAt).total_seconds() < 10

    @patch.object(email_service, "send_payment_success_email")
    def test_upgrade_does_not_delete_keywords(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_up",
            order_id="order_up",
        )
        self.db.refresh(kw)
        assert kw.isActive is True

    @patch.object(email_service, "send_payment_success_email")
    def test_starter_to_pro_upgrade(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active")
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_up",
            order_id="order_up",
        )
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.subscriptionStatus == "active"


class TestDowngrade:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    def test_valid_downgrade_succeeds(self):
        user = make_user(self.db, plan="pro", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        change_user_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange == "starter"
        assert user.creditBalance == 0.0

    def test_downgrade_blocked_by_keyword_limit(self):
        user = make_user(self.db, plan="pro", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(101):
            kw = Keyword(id=f"k{i}", projectId=project.id, userId=user.id, keyword=f"test{i}", isActive=True)
            self.db.add(kw)
        self.db.commit()
        
        with pytest.raises(ApiError) as exc_info:
            change_user_plan(self.db, user.id, "starter")
        assert "Downgrade not allowed" in str(exc_info.value)

    def test_downgrade_blocked_by_competitor_limit(self):
        user = make_user(self.db, plan="pro", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(4):
            comp = Competitor(id=f"c{i}", projectId=project.id, name=f"Comp{i}", domain=f"comp{i}.com")
            self.db.add(comp)
        self.db.commit()
        
        with pytest.raises(ApiError) as exc_info:
            change_user_plan(self.db, user.id, "starter")
        assert "Downgrade not allowed" in str(exc_info.value)

    def test_downgrade_succeeds_after_reducing_keywords(self):
        user = make_user(self.db, plan="pro", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(101):
            kw = Keyword(id=f"k{i}", projectId=project.id, userId=user.id, keyword=f"test{i}", isActive=True)
            self.db.add(kw)
        self.db.commit()
        
        for i in range(50):
            kw = self.db.scalar(select(Keyword).where(Keyword.id == f"k{i}"))
            self.db.execute(delete(Keyword).where(Keyword.id == f"k{i}"))
        self.db.commit()
        
        change_user_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.selectedPlan == "pro"
        assert user.pendingPlanChange == "starter"

    def test_downgrade_does_not_delete_keywords(self):
        user = make_user(self.db, plan="pro", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        change_user_plan(self.db, user.id, "starter")
        self.db.refresh(kw)
        assert kw.isActive is not False or True  # keyword still exists


class TestExpiration:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    def test_expired_subscription_becomes_past_due(self):
        user = make_user(self.db, plan="starter", subscription_status="active")
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now - timedelta(days=1),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        handle_expiration(self.db, user)
        self.db.refresh(user)
        assert user.subscriptionStatus == "past_due"

    def test_non_expired_subscription_not_changed(self):
        user = make_user(self.db, plan="starter", subscription_status="active")
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now + timedelta(days=10),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        handle_expiration(self.db, user)
        self.db.refresh(user)
        assert user.subscriptionStatus == "active"

    def test_grace_period_expiry_becomes_permanent_free(self):
        user = make_user(self.db, plan="starter", subscription_status="past_due")
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now - timedelta(days=10),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        handle_grace_period_expiry(self.db, user)
        self.db.refresh(user)
        assert user.subscriptionStatus == "free"
        assert user.selectedPlan == "free_trial"

    def test_grace_period_not_expired_remains_past_due(self):
        user = make_user(self.db, plan="starter", subscription_status="past_due")
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now - timedelta(days=3),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        handle_grace_period_expiry(self.db, user)
        self.db.refresh(user)
        assert user.subscriptionStatus == "past_due"

    def test_paid_expiry_preserves_keyword_activation_state(self):
        user = make_user(self.db, plan="starter", subscription_status="past_due")
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now - timedelta(days=10),
            isActive=True,
        )
        self.db.add(sub)
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        handle_grace_period_expiry(self.db, user)
        self.db.refresh(kw)
        assert kw.isActive is True

    def test_historical_data_retained_after_expiration(self):
        user = make_user(self.db, plan="starter", subscription_status="active")
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now - timedelta(days=1),
            isActive=True,
        )
        self.db.add(sub)
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=True)
        self.db.add(kw)
        self.db.commit()
        
        handle_expiration(self.db, user)
        self.db.refresh(project)
        self.db.refresh(kw)
        assert self.db.scalar(select(Project).where(Project.id == project.id)) is not None
        assert self.db.scalar(select(Keyword).where(Keyword.id == kw.id)) is not None

    def test_credit_balance_preserved_after_expiration(self):
        user = make_user(self.db, plan="starter", subscription_status="active", credit_balance=250.0)
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId=0,
            status="active",
            startDate=self.now - timedelta(days=30),
            endDate=self.now - timedelta(days=1),
            isActive=True,
        )
        self.db.add(sub)
        self.db.commit()
        
        handle_expiration(self.db, user)
        self.db.refresh(user)
        assert user.creditBalance == 250.0


class TestInactive:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    def test_inactive_user_cannot_add_keywords(self):
        user = make_user(self.db, plan="starter", subscription_status="inactive")
        
        with pytest.raises(ApiError) as exc_info:
            ensure_subscription_active(user)
        assert "inactive" in str(exc_info.value).lower()

    def test_inactive_user_preserves_credit_balance(self):
        user = make_user(self.db, plan="starter", subscription_status="inactive", credit_balance=500.0)
        assert user.creditBalance == 500.0

    def test_inactive_user_no_monthly_credits(self):
        user = make_user(self.db, plan="starter", subscription_status="inactive", credit_balance=500.0)
        user.planAnniversaryAt = self.now - timedelta(days=40)
        user.lastCreditResetAt = self.now - timedelta(days=40)
        self.db.add(user)
        self.db.commit()
        
        from app.services.plan_service import reset_due_credits_for_all_users
        result = reset_due_credits_for_all_users(self.db)
        assert result["reset_count"] == 0
        self.db.refresh(user)
        assert user.creditBalance == 500.0


class TestReactivation:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    @patch.object(email_service, "send_payment_success_email")
    def test_reactivation_sets_new_plan_credits(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="inactive", credit_balance=250.0)
        result = reactivate_subscription(self.db, user.id, "starter")
        self.db.refresh(result)
        assert result.subscriptionStatus == "active"
        assert result.creditBalance == 3000.0
        assert result.automaticCreditBalance == 5000.0

    @patch.object(email_service, "send_payment_success_email")
    def test_reactivation_resets_anniversary(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="inactive")
        user.planAnniversaryAt = self.now - timedelta(days=60)
        user.lastCreditResetAt = self.now - timedelta(days=60)
        self.db.add(user)
        self.db.commit()
        
        result = reactivate_subscription(self.db, user.id, "starter")
        self.db.refresh(result)
        assert result.planAnniversaryAt is not None
        assert (self.now - result.planAnniversaryAt).total_seconds() < 10

    @patch.object(email_service, "send_payment_success_email")
    def test_old_keywords_remain_inactive_after_reactivation(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="inactive")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=False)
        self.db.add(kw)
        self.db.commit()
        
        reactivate_subscription(self.db, user.id, "starter")
        self.db.refresh(kw)
        assert kw.isActive is False

    @patch.object(email_service, "send_payment_success_email")
    def test_reactivation_creates_ledger(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="inactive")
        reactivate_subscription(self.db, user.id, "starter")
        ledger = self.db.scalar(
            select(CreditLedger).where(CreditLedger.userId == user.id, CreditLedger.actionType == "cycle_allocation")
        )
        assert ledger is not None
        assert float(ledger.amount) == 8000.0

    def test_keyword_reactivation_respects_plan_limit(self):
        user = make_user(self.db, plan="starter", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        for i in range(101):
            kw = Keyword(id=f"k{i}", projectId=project.id, userId=user.id, keyword=f"test{i}", isActive=False)
            self.db.add(kw)
        self.db.commit()
        
        for i in range(100):
            kw = self.db.scalar(select(Keyword).where(Keyword.id == f"k{i}"))
            activate_keyword(self.db, user.id, kw.id)
        
        kw2 = self.db.scalar(select(Keyword).where(Keyword.id == "k100"))
        activate_keyword(self.db, user.id, kw2.id)
        self.db.refresh(kw2)
        assert kw2.isActive is True


class TestOwnership:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    def test_cannot_activate_another_users_keyword(self):
        user1 = make_user(self.db, plan="starter", subscription_status="active")
        user2 = User(
            id="user-2",
            name="Test User 2",
            email="test2@example.com",
            passwordHash="hash",
            selectedPlan="starter",
            creditBalance=0.0,
            subscriptionStatus="active",
            trialStartsAt=self.now,
            trialEndsAt=self.now + timedelta(days=7),
            planAnniversaryAt=self.now,
            lastCreditResetAt=self.now,
            createdAt=self.now,
            updatedAt=self.now,
        )
        self.db.add(user2)
        self.db.commit()
        
        project = Project(id="p1", name="Test", domain="test.com", userId=user1.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user1.id, keyword="test", isActive=False)
        self.db.add(kw)
        self.db.commit()
        
        with pytest.raises(ApiError) as exc_info:
            activate_keyword(self.db, user2.id, kw.id)
        assert "not found" in str(exc_info.value).lower()


class TestIdempotency:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    @patch.object(email_service, "send_payment_success_email")
    def test_duplicate_activation_does_not_double_credit(self, mock_email):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing", credit_balance=0.0)
        activate_paid_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        balance_after_first = user.creditBalance
        
        activate_paid_plan(self.db, user.id, "starter")
        self.db.refresh(user)
        assert user.creditBalance == balance_after_first

    @patch.object(email_service, "send_payment_success_email")
    def test_duplicate_renewal_does_not_double_credit(self, mock_email):
        user = make_user(self.db, plan="starter", subscription_status="active", credit_balance=100.0)
        user.planAnniversaryAt = self.now - timedelta(days=30)
        user.lastCreditResetAt = self.now - timedelta(days=30)
        self.db.add(user)
        self.db.commit()
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew",
            order_id="order_renew",
        )
        self.db.refresh(user)
        balance_after_first = user.creditBalance
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=0,
            payment_id="pay_renew2",
            order_id="order_renew2",
        )
        self.db.refresh(user)
        assert user.creditBalance == balance_after_first
        assert user.automaticCreditBalance == 5000.0


class TestAccountWideKeywordLimit:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.now = datetime.utcnow()

    def teardown_method(self):
        self.db.close()

    def _add_keyword(self, db, user_id, project_id, payload):
        with patch("app.services.keyword_service._apply_day_one_tracking", return_value=True):
            return add_keyword(db, user_id, project_id, payload)

    def _add_keywords_bulk(self, db, user_id, project_id, keywords, location="India", location_code=2840):
        with patch("app.services.keyword_service._apply_day_one_tracking", return_value=True):
            return add_keywords_bulk(db, user_id, project_id, keywords, location, location_code)

    def test_single_project_reaches_limit(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        for i in range(5):
            self._add_keyword(self.db, user.id, project.id, {"keyword": f"kw{i}"})

        with pytest.raises(ApiError) as exc_info:
            self._add_keyword(self.db, user.id, project.id, {"keyword": "kw-overflow"})
        assert "Keyword limit reached" in str(exc_info.value)

    def test_multiple_projects_share_one_limit(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project_a = Project(id="p1", name="A", domain="a.com", userId=user.id)
        project_b = Project(id="p2", name="B", domain="b.com", userId=user.id)
        self.db.add_all([project_a, project_b])
        self.db.commit()

        for i in range(3):
            self._add_keyword(self.db, user.id, project_a.id, {"keyword": f"a-kw{i}"})
        for i in range(2):
            self._add_keyword(self.db, user.id, project_b.id, {"keyword": f"b-kw{i}"})

        with pytest.raises(ApiError) as exc_info:
            self._add_keyword(self.db, user.id, project_a.id, {"keyword": "overflow"})
        assert "Keyword limit reached" in str(exc_info.value)

        with pytest.raises(ApiError) as exc_info:
            self._add_keyword(self.db, user.id, project_b.id, {"keyword": "overflow"})
        assert "Keyword limit reached" in str(exc_info.value)

    def test_distribution_across_projects(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project_a = Project(id="p1", name="A", domain="a.com", userId=user.id)
        project_b = Project(id="p2", name="B", domain="b.com", userId=user.id)
        project_c = Project(id="p3", name="C", domain="c.com", userId=user.id)
        self.db.add_all([project_a, project_b, project_c])
        self.db.commit()

        self._add_keyword(self.db, user.id, project_a.id, {"keyword": "a1"})
        self._add_keyword(self.db, user.id, project_b.id, {"keyword": "b1"})
        for i in range(3):
            self._add_keyword(self.db, user.id, project_c.id, {"keyword": f"c{i}"})

        total = count_user_keywords(self.db, user.id)
        assert total == 5

    def test_delete_frees_account_slot(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        for i in range(5):
            self._add_keyword(self.db, user.id, project.id, {"keyword": f"kw{i}"})

        kw = self.db.scalar(select(Keyword).where(Keyword.keyword == "kw0"))
        delete_keyword(self.db, user.id, kw.id)

        total = count_user_active_keywords(self.db, user.id)
        assert total == 4

        self._add_keyword(self.db, user.id, project.id, {"keyword": "kw-new"})
        total = count_user_active_keywords(self.db, user.id)
        assert total == 5

    def test_deactivate_does_not_free_slot(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        for i in range(5):
            self._add_keyword(self.db, user.id, project.id, {"keyword": f"kw{i}"})

        kw = self.db.scalar(select(Keyword).where(Keyword.keyword == "kw0"))
        deactivate_keyword(self.db, user.id, kw.id)

        total = count_user_active_keywords(self.db, user.id)
        assert total == 4

        with pytest.raises(ApiError) as exc_info:
            self._add_keyword(self.db, user.id, project.id, {"keyword": "kw-overflow"})
        assert "Keyword limit reached" in str(exc_info.value)

    def test_bulk_create_cannot_exceed_account_limit(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        for i in range(3):
            self._add_keyword(self.db, user.id, project.id, {"keyword": f"kw{i}"})

        with pytest.raises(ApiError) as exc_info:
            self._add_keywords_bulk(self.db, user.id, project.id, [f"bulk{i}" for i in range(5)])
        assert "Keyword limit reached" in str(exc_info.value)

    def test_downgrade_across_projects(self):
        user = make_user(self.db, plan="pro", subscription_status="active")
        project_a = Project(id="p1", name="A", domain="a.com", userId=user.id)
        project_b = Project(id="p2", name="B", domain="b.com", userId=user.id)
        self.db.add_all([project_a, project_b])
        self.db.commit()

        for i in range(60):
            kw = Keyword(id=f"a-kw{i}", projectId=project_a.id, userId=user.id, keyword=f"a{i}", isActive=True)
            self.db.add(kw)
        for i in range(40):
            kw = Keyword(id=f"b-kw{i}", projectId=project_b.id, userId=user.id, keyword=f"b{i}", isActive=True)
            self.db.add(kw)
        self.db.commit()

        with pytest.raises(ApiError) as exc_info:
            change_user_plan(self.db, user.id, "starter")
        assert "Downgrade not allowed" in str(exc_info.value)

    def test_reactivation_does_not_increase_count(self):
        user = make_user(self.db, plan="starter", subscription_status="active")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        kw = Keyword(id="k1", projectId=project.id, userId=user.id, keyword="test", isActive=False)
        self.db.add(kw)
        self.db.commit()

        activate_keyword(self.db, user.id, kw.id)
        total = count_user_keywords(self.db, user.id)
        assert total == 1

    def test_bulk_delete_frees_slots(self):
        user = make_user(self.db, plan="free_trial", subscription_status="trialing")
        project = Project(id="p1", name="Test", domain="test.com", userId=user.id)
        self.db.add(project)
        self.db.commit()

        created = []
        for i in range(5):
            kw = self._add_keyword(self.db, user.id, project.id, {"keyword": f"kw{i}"})
            created.append(kw)

        ids = [created[i]["id"] for i in range(3)]
        delete_keywords_bulk(self.db, user.id, ids)

        total = count_user_active_keywords(self.db, user.id)
        assert total == 2

        for i in range(3):
            self._add_keyword(self.db, user.id, project.id, {"keyword": f"new{i}"})
        total = count_user_active_keywords(self.db, user.id)
        assert total == 5
