import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

from app.db.models import Base, User, Subscription
from app.services.plan_service import validate_plan_change, change_user_plan, PLAN_DEFINITIONS
from app.services.payment_service import activate_subscription


def make_user(db: Session, plan="pro", subscription_active=True, end_date=None, credit_balance=0.0):
    if end_date is None:
        end_date = datetime.utcnow() + timedelta(days=30)
    user = User(
        id="user-1",
        name="Test User",
        email="test@example.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        subscriptionStatus="active",
    )
    if subscription_active:
        sub = Subscription(
            id="sub-1",
            userId=user.id,
            planId={"starter": 0, "pro": 1, "agency": 2}[plan],
            status="active",
            startDate=datetime.utcnow(),
            endDate=end_date,
            isActive=True,
        )
        user.subscriptions = [sub]
    db.add(user)
    if subscription_active:
        db.add(sub)
    db.commit()
    db.refresh(user)
    return user


class TestPlanChange:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def teardown_method(self):
        self.db.close()

    def test_downgrade_sets_pending_plan_change(self):
        user = make_user(self.db, plan="pro")
        result = change_user_plan(self.db, user.id, "starter")
        assert result.selectedPlan == "pro"  # immediate plan unchanged
        assert result.pendingPlanChange == "starter"
        assert result.creditBalance == 0.0

    def test_downgrade_blocked_by_usage(self):
        user = make_user(self.db, plan="pro")
        # Create 2 projects to exceed starter limit of 1
        from app.db.models import Project
        for i in range(2):
            project = Project(id=f"p{i}", name=f"Test {i}", domain=f"test{i}.com", userId=user.id)
            self.db.add(project)
        self.db.commit()
        
        with pytest.raises(Exception):
            change_user_plan(self.db, user.id, "starter")

    def test_upgrade_is_immediate(self):
        user = make_user(self.db, plan="starter")
        result = change_user_plan(self.db, user.id, "pro")
        assert result.selectedPlan == "pro"
        assert result.pendingPlanChange is None

    def test_activate_subscription_applies_pending_downgrade(self):
        user = make_user(self.db, plan="pro", end_date=datetime.utcnow() + timedelta(days=30))
        change_user_plan(self.db, user.id, "starter")
        assert user.pendingPlanChange == "starter"
        
        activate_subscription(
            db=self.db,
            user_id=user.id,
            plan_id=1,
            payment_id="pay_test",
            order_id="order_test"
        )
        self.db.refresh(user)
        assert user.selectedPlan == "starter"
        assert user.pendingPlanChange is None

    def test_activate_subscription_without_pending_change(self):
        user = make_user(self.db, plan="starter")
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

    def test_downgrade_same_plan_no_pending(self):
        user = make_user(self.db, plan="starter")
        result = change_user_plan(self.db, user.id, "starter")
        assert result.selectedPlan == "starter"
        assert result.pendingPlanChange is None
