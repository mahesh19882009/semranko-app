"""Phase C public-pricing configuration and payment safety coverage."""

import asyncio
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.routes.payments import create_payment_order
from app.db.models import Base, PaymentOrder, User
from app.services.payment_service import activate_subscription
from app.services.plan_service import list_available_plans


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db):
    user = User(id="phase-c-user", name="Phase C", email="phase-c@example.com", passwordHash="hash")
    db.add(user)
    db.commit()
    return user


def test_public_plan_prices_are_explicit_and_annual_is_eleven_months():
    plans = {plan["key"]: plan for plan in list_available_plans()}
    assert plans["free_trial"]["monthlyPrice"] == plans["free_trial"]["yearlyPrice"] == 0
    assert plans["free_trial"]["monthlyPriceUsd"] == plans["free_trial"]["yearlyPriceUsd"] == 0
    for key in ("starter", "pro", "agency"):
        assert plans[key]["yearlyPrice"] == plans[key]["monthlyPrice"] * 11
        assert plans[key]["yearlyPriceUsd"] == plans[key]["monthlyPriceUsd"] * 11


@pytest.mark.parametrize("billing_cycle", ["monthly", "yearly"])
def test_usd_checkout_is_safely_rejected_until_provider_support_is_enabled(billing_cycle):
    db = _db()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(create_payment_order(plan_id=0, amount=1, billing_cycle=billing_cycle, currency="USD", current_user=_user(db), db=db))
    assert exc.value.status_code == 409
    assert exc.value.detail["error"] == "USD_CHECKOUT_UNAVAILABLE"


@pytest.mark.parametrize(("billing_cycle", "expected_amount"), [("monthly", 117882), ("yearly", 1296702)])
def test_inr_order_uses_server_price_not_browser_amount_and_persists_cycle(billing_cycle, expected_amount):
    db = _db()
    user = _user(db)
    order_id = f"order-phase-c-{billing_cycle}"
    with patch("app.api.routes.payments.create_order", return_value={"id": order_id, "amount": expected_amount, "currency": "INR", "key": "test"}):
        result = asyncio.run(create_payment_order(plan_id=0, amount=1, billing_cycle=billing_cycle, currency="INR", current_user=user, db=db))
    assert result["amount"] == expected_amount
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
    assert order.amount == expected_amount
    assert order.billingCycle == billing_cycle


def test_annual_subscription_uses_a_365_day_period(monkeypatch):
    db = _db()
    user = _user(db)
    monkeypatch.setattr("app.services.payment_service.email_service.send_payment_success_email", lambda **kwargs: None)

    subscription = activate_subscription(
        db=db,
        user_id=user.id,
        plan_id=0,
        payment_id="payment-phase-c",
        order_id="order-subscription-phase-c",
        billing_cycle="yearly",
    )

    assert subscription.endDate - subscription.startDate == timedelta(days=365)
