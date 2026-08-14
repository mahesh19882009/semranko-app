"""Focused commercial configuration invariants and order-source coverage."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.deps import require_admin
from app.api.routes.admin_commercial import update_plan, update_top_up_package
from app.api.routes.payments import create_payment_order, create_top_up_order
from app.core.errors import ApiError
from app.db.models import Base, PaymentOrder, TopUpPackage, User
from app.services.commercial_config_service import ensure_commercial_config, list_top_up_packages
from app.services.profitability_reporting_service import calculate_plan_profitability


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db, user_id="admin", admin=False):
    user = User(id=user_id, name=user_id, email=f"{user_id}@example.com", passwordHash="hash", isAdmin=admin)
    db.add(user); db.commit()
    return user


def test_admin_authorization_and_plan_price_order_source():
    db = _db(); admin = _user(db, admin=True); normal = _user(db, "normal")
    with pytest.raises(ApiError):
        require_admin(current_user={"id": normal.id}, db=db)
    assert require_admin(current_user={"id": admin.id}, db=db).id == admin.id
    ensure_commercial_config(db)
    payload = {"monthlyPriceInr": 1200}
    updated = update_plan("starter", payload, db, admin)["data"]
    assert updated["monthlyPriceInr"] == 1200
    assert updated["yearlyPriceInr"] == 13200
    with patch("app.api.routes.payments.create_order", return_value={"id": "commercial-order", "amount": 141600, "currency": "INR", "key": "test"}):
        order = asyncio.run(create_payment_order(plan_id=0, amount=1, billing_cycle="monthly", currency="INR", current_user=admin, db=db))
    assert order["amount"] == 141600  # ₹1200 plus the existing INR GST
    assert db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == "commercial-order")).amount == 141600


def test_plan_validation_and_historical_order_protection():
    db = _db(); admin = _user(db, admin=True); ensure_commercial_config(db)
    historical = PaymentOrder(userId=admin.id, razorpayOrderId="historic", planId=0, amount=117882, currency="INR", status="paid")
    db.add(historical); db.commit()
    with pytest.raises(HTTPException, match="Automatic reserved"):
        update_plan("starter", {"monthlyCredits": 10, "automaticCredits": 11}, db, admin)
    with pytest.raises(HTTPException, match="cannot be negative"):
        update_plan("starter", {"monthlyPriceUsd": -1}, db, admin)
    update_plan("starter", {"monthlyPriceUsd": 17}, db, admin)
    db.refresh(historical)
    assert historical.amount == 117882


def test_active_packages_are_authoritative_and_inactive_packages_cannot_be_bought():
    db = _db(); admin = _user(db, admin=True); ensure_commercial_config(db)
    package = list_top_up_packages(db)[0]
    with patch("app.api.routes.payments.create_order", return_value={"id": "topup-order", "amount": 11800, "currency": "INR", "key": "test"}):
        result = asyncio.run(create_top_up_order(package_id=package.id, currency="INR", current_user=admin, db=db))
    assert result["total_credits"] == package.credits
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == "topup-order"))
    assert order.topUpPackageId == package.id
    update_top_up_package(package.id, {"isActive": False}, db, admin)
    assert package.id not in {item.id for item in list_top_up_packages(db)}
    with pytest.raises(HTTPException):
        asyncio.run(create_top_up_order(package_id=package.id, currency="INR", current_user=admin, db=db))
    assert db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == "topup-order")).topUpPackageId == package.id


def test_profitability_plan_metadata_uses_current_admin_configuration():
    db = _db(); admin = _user(db, admin=True)
    update_plan("starter", {"monthlyPriceInr": 1200, "projectLimit": 2,
                            "keywordLimit": 150, "monthlyCredits": 9000}, db, admin)
    result = calculate_plan_profitability(db, "starter", days=30)
    assert result["monthly_price_inr"] == 1200
    assert result["yearly_price_inr"] == 13200
    assert result["domain_limit"] == 2
    assert result["keyword_limit"] == 150
    assert result["monthly_credits"] == 9000
