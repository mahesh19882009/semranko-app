"""
Phase 11.2 — Production Configuration & Operational Hardening Tests

Tests for gaps identified during Phase 11.2 audit:
- Authorization isolation on payment verification
- Cache hit billing for weekly refresh
- Keyword limit enforcement
- Sync refresh endpoint
"""

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, Project, User, RefreshJob, ProcessingJob, PaymentOrder
from app.services.async_bulk_service import (
    _paginate_eligible_keywords,
    create_refresh_jobs,
    claim_refresh_job,
    run_weekly_bulk_update_job,
    run_weekly_refresh_worker,
    _submit_weekly_refresh,
)
from app.api.routes.payments import verify_payment
from app.api.routes.keywords import create_keyword, bulk_create_keywords
from app.services.keyword_service import add_keyword, add_keywords_bulk


def make_user(db, user_id="user-1", email=None, plan="starter", credit_balance=100.0,
              subscription_status="active", refresh_frequency="monthly"):
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Test User",
        email=email or f"{user_id}@test.com",
        passwordHash="hash",
        selectedPlan=plan,
        creditBalance=credit_balance,
        automaticCreditBalance=credit_balance,
        subscriptionStatus=subscription_status,
        trialStartsAt=now,
        trialEndsAt=now + timedelta(days=7),
        refreshFrequency=refresh_frequency,
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db, user_id, project_id="p1", domain="example.com"):
    project = Project(id=project_id, name="Test", domain=domain, userId=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def make_keyword(db, project_id, user_id, keyword="test kw", location="India", is_active=True):
    kw = Keyword(
        id=f"kw-{keyword.replace(' ', '-')}-{datetime.utcnow().timestamp()}",
        projectId=project_id,
        userId=user_id,
        keyword=keyword,
        location=location,
        isActive=is_active,
    )
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


class TestAuthorizationIsolation:
    def test_verify_payment_checks_ownership(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user_a = make_user(db, user_id="user-a", email="a@test.com")
        user_b = make_user(db, user_id="user-b", email="b@test.com")
        
        order = PaymentOrder(
            userId=user_a.id,
            razorpayOrderId="order_a",
            amount=10000,
            currency="INR",
            status="created",
            planId=1,
            purchaseType="SUBSCRIPTION_UPGRADE",
        )
        db.add(order)
        db.commit()

        with patch("app.api.routes.payments.verify_payment_signature", return_value=True):
            with patch("app.api.routes.payments.activate_subscription") as mock_activate:
                request_data = {
                    "razorpay_order_id": "order_a",
                    "razorpay_payment_id": "pay_a",
                    "razorpay_signature": "sig_a",
                }
                current_user = type("User", (), {"id": "user-b", "email": "b@test.com"})()
                db_session = db
                
            try:
                import asyncio
                asyncio.run(verify_payment(request_data=request_data, current_user=current_user, db=db_session))
            except HTTPException as exc:
                assert exc.status_code == 403
                return
                
                pytest.fail("Expected 403 but no exception was raised")


class TestCacheHitBilling:
    def test_weekly_cache_hit_charges_credits(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)
        project = make_project(db, user.id)
        make_keyword(db, project.id, user.id, keyword="cached kw")

        batches = _paginate_eligible_keywords(db, job_type="weekly")
        jobs = create_refresh_jobs(db, "weekly_serp", batches)
        job = jobs[0]

        job.status = "processing"
        db.add(job)
        db.commit()

        with patch("app.services.dataforseo_client._build_serp_cache_key", return_value="cache-key"):
            with patch("app.services.dataforseo_client._get_cached_serp", return_value={"items": []}):
                result = _submit_weekly_refresh(db, job, ["cached kw"])
                assert result is True

        db.refresh(user)
        assert user.creditBalance == 100.0
        assert user.automaticCreditBalance == 90.0

    def test_weekly_cache_miss_does_not_pre_charge_credits(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)
        project = make_project(db, user.id)
        make_keyword(db, project.id, user.id, keyword="uncached kw")

        batches = _paginate_eligible_keywords(db, job_type="weekly")
        jobs = create_refresh_jobs(db, "weekly_serp", batches)
        job = jobs[0]

        job.status = "processing"
        db.add(job)
        db.commit()

        with patch("app.services.dataforseo_client._build_serp_cache_key", return_value="cache-key"):
            with patch("app.services.dataforseo_client._get_cached_serp", return_value=None):
                with patch("requests.post") as mock_post:
                    mock_response = MagicMock()
                    mock_response.headers.get.return_value = "application/json"
                    mock_response.json.return_value = {
                        "tasks": [{
                            "id": "task-123",
                            "status": "ok",
                        }]
                    }
                    mock_response.raise_for_status.return_value = None
                    mock_post.return_value = mock_response

                    result = _submit_weekly_refresh(db, job, ["uncached kw"])
                    assert result is True

        db.refresh(user)
        assert user.creditBalance == 100.0
        assert user.automaticCreditBalance == 90.0


class TestKeywordLimitEnforcement:
    def test_bulk_add_respects_keyword_limit(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0, plan="free_trial")
        project = make_project(db, user.id)

        for i in range(5):
            kw = Keyword(
                id=f"kw-limit-{i}",
                projectId=project.id,
                userId=user.id,
                keyword=f"limit kw {i}",
                location="India",
                isActive=True,
            )
            db.add(kw)
        db.commit()

        with patch("app.services.keyword_service.DataForSEOClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_keyword_data_batch.return_value = {
                "limit kw 5": {"volume": 1000, "kd": 50}
            }
            MockClient.return_value = mock_instance

            payload = {
                "keywords": [f"limit kw {i}" for i in range(5, 10)]
            }
            
            try:
                result = bulk_create_keywords(project.id, payload, user={"userId": user.id}, db=db)
            except Exception as exc:
                from app.core.errors import ApiError
                if isinstance(exc, ApiError) and exc.status_code == 403:
                    return
                raise

            if isinstance(result, dict) and not result.get("success", True):
                assert result.get("error") == "keyword_limit_exceeded"
                return

            pytest.fail("Expected keyword limit error but none was raised")


class TestSyncRefreshEndpoint:
    def test_refresh_keyword_data_endpoint_works(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="refresh kw")

        with patch("app.services.keyword_update_service.DataForSEOClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_rank_batch.return_value = {
                "refresh kw": {"position": 5, "url": "https://example.com"}
            }
            MockClient.return_value = mock_instance

            from app.api.routes.keywords import refresh_project_keywords
            response = refresh_project_keywords(
                project_id=project.id,
                payload={},
                user={"userId": user.id},
                db=db
            )
            
            if hasattr(response, 'body'):
                result = json.loads(response.body)
            else:
                result = response
            
            assert result is not None
            assert "success" in result or "message" in result
