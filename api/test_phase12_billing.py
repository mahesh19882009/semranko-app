"""
Phase 12 — Billing, Credit, Abuse & Account Verification Hardening Tests

Tests for:
- Cache-hit billing
- Double-billing protection
- Mobile verification
- Email verification enforcement
- Keyword limit enforcement
- Database constraints
- Credit ledger integrity
"""

import sys
sys.path.insert(0, "/Users/maheshsharma/development/rankcare-api/api/fastapi_app")

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import func

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.orm import Session

from app.db.models import Base, Keyword, Project, User, RefreshJob, CreditLedger
from app.services.async_bulk_service import (
    _paginate_eligible_keywords,
    create_refresh_jobs,
    _submit_weekly_refresh,
)
from app.services.credit_service import deduct_credits, reserve_credits, consume_reserved, refund_reserved
from app.services.auth_service import create_mobile_verification_session, login_user, register_user
from app.services.otp_service import send_otp, verify_otp, resend_otp, _normalize_mobile
from app.core.errors import ApiError
from app.core.security import decode_access_token


def make_user(db, user_id="user-1", email=None, plan="starter", credit_balance=100.0,
              subscription_status="active", refresh_frequency="monthly", is_verified=True, mobile_verified=False):
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
        isVerified=is_verified,
        mobileVerified=mobile_verified,
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

    def test_weekly_cache_miss_no_pre_charge(self):
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


class TestDoubleBillingProtection:
    def test_same_task_id_not_charged_twice(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)

        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge",
            task_id="task-123",
        )
        db.refresh(user)
        balance_after_first = user.creditBalance

        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge retry",
            task_id="task-123",
        )
        db.refresh(user)
        balance_after_second = user.creditBalance

        assert balance_after_first == balance_after_second
        assert balance_after_first == 90.0

    def test_different_task_ids_charged_separately(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)

        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge 1",
            task_id="task-123",
        )
        db.refresh(user)
        balance_after_first = user.creditBalance

        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge 2",
            task_id="task-456",
        )
        db.refresh(user)
        balance_after_second = user.creditBalance

        assert balance_after_second == 80.0


class TestMobileVerification:
    def test_send_otp_creates_otp_record(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, is_verified=True, mobile_verified=False)

        with patch("app.services.otp_service.requests.get") as mock_get:
            with patch("app.services.otp_service.settings") as mock_settings:
                mock_settings.TWOFACTOR_API_KEY = "test-api-key"
                mock_response = MagicMock()
                mock_response.json.return_value = {"Status": "Success", "SessionId": "session-123", "OTP": "123456"}
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                result = send_otp(db, user.id, "+919876543210")
                assert result["success"] is True
                assert result["session_id"] == "session-123"

        db.refresh(user)
        assert user.mobileNumber == "919876543210"
        assert user.mobileVerificationOtp == "session-123"
        assert user.mobileVerificationExpiresAt is not None

    def test_verify_otp_marks_mobile_verified(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, is_verified=True, mobile_verified=False)
        user.mobileNumber = "919876543210"
        user.mobileVerificationOtp = "123456"
        user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
        db.add(user)
        db.commit()

        with patch("app.services.otp_service.requests.get") as mock_get:
            with patch("app.services.otp_service.settings") as mock_settings:
                mock_settings.TWOFACTOR_API_KEY = "test-api-key"
                mock_response = MagicMock()
                mock_response.json.return_value = {"Status": "Success", "Details": "OTP matched"}
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                result = verify_otp(db, user.id, "123456")
                assert result["success"] is True

        db.refresh(user)
        assert user.mobileVerified is True
        assert user.mobileVerificationOtp is None

    def test_expired_otp_rejected(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, is_verified=True, mobile_verified=False)
        user.mobileNumber = "919876543210"
        user.mobileVerificationOtp = "123456"
        user.mobileVerificationExpiresAt = datetime.utcnow() - timedelta(minutes=1)
        db.add(user)
        db.commit()

        with pytest.raises(ApiError) as exc_info:
            verify_otp(db, user.id, "123456")
        assert exc_info.value.status_code == 400
        assert exc_info.value.data["error"] == "OTP_EXPIRED"

    def test_duplicate_mobile_rejected(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user1 = make_user(db, user_id="user-1", email="u1@test.com")
        user2 = make_user(db, user_id="user-2", email="u2@test.com")

        user1.mobileNumber = "919876543210"
        user1.mobileVerified = True
        db.add(user1)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            send_otp(db, user2.id, "+919876543210")
        assert exc_info.value.status_code == 409


class TestEmailVerificationEnforcement:
    def test_login_requires_email_verification(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, is_verified=False, mobile_verified=True)

        with patch("app.services.auth_service.verify_password", return_value=True):
            with pytest.raises(ApiError) as exc_info:
                login_user(db, {"email": user.email, "password": "password"})
            assert exc_info.value.status_code == 403
            assert exc_info.value.data["error"] == "EMAIL_VERIFICATION_REQUIRED"
            assert exc_info.value.data["action"] == "resend_verification"

    def test_login_requires_mobile_verification(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, is_verified=True, mobile_verified=False)

        with patch("app.services.auth_service.verify_password", return_value=True):
            with pytest.raises(ApiError) as exc_info:
                login_user(db, {"email": user.email, "password": "password"})
            assert exc_info.value.status_code == 403
            assert exc_info.value.data["error"] == "MOBILE_VERIFICATION_REQUIRED"
            assert exc_info.value.data["action"] == "verify_mobile"

    def test_old_account_can_create_purpose_scoped_mobile_recovery_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)
        user = make_user(db, is_verified=True, mobile_verified=False)

        with patch("app.services.auth_service.verify_password", return_value=True):
            result = create_mobile_verification_session(
                db, {"email": user.email, "password": "password"}
            )

        token_payload = decode_access_token(result["mobileVerificationToken"])
        assert result["mobileVerified"] is False
        assert token_payload["userId"] == user.id
        assert token_payload["purpose"] == "mobile_verification"


class TestKeywordLimitEnforcement:
    def test_keyword_limit_enforced_at_db_level(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="free_trial")
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

        from app.core.security import enforce_limits
        from app.core.errors import ApiError

        with pytest.raises(ApiError) as exc_info:
            enforce_limits(resource_type='keyword')(lambda **kwargs: None)(
                db=db,
                user=user,
            )
        assert exc_info.value.status_code == 403


class TestCreditLedgerIntegrity:
    def test_deduct_credits_creates_ledger_entry(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)

        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge",
            task_id="task-ledger-1",
        )

        ledger = db.scalar(
            select(CreditLedger).where(CreditLedger.taskId == "task-ledger-1")
        )
        assert ledger is not None
        assert ledger.amount == -10.0
        assert ledger.balanceBefore == 100.0
        assert ledger.balanceAfter == 90.0

    def test_duplicate_task_id_does_not_create_duplicate_ledger(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, credit_balance=100.0)

        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge 1",
            task_id="task-dup-1",
        )
        deduct_credits(
            db=db,
            user_id=user.id,
            amount=10.0,
            action_type="charge",
            description="Test charge 2",
            task_id="task-dup-1",
        )

        count = db.scalar(
            select(func.count()).select_from(CreditLedger).where(CreditLedger.taskId == "task-dup-1")
        )
        assert count == 1


class TestMobileNormalization:
    def test_normalize_mobile_india_10_digits(self):
        assert _normalize_mobile("9876543210") == "919876543210"

    def test_normalize_mobile_with_country_code(self):
        assert _normalize_mobile("+919876543210") == "919876543210"

    def test_normalize_mobile_with_spaces(self):
        assert _normalize_mobile("+91 98765 43210") == "919876543210"

    def test_normalize_mobile_already_normalized(self):
        assert _normalize_mobile("919876543210") == "919876543210"


class TestKeywordReaddCooldown:
    def test_soft_deleted_keyword_cannot_be_readded_within_cooldown(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="free_trial")
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="cooldown kw")

        kw.isActive = False
        kw.deletedAt = datetime.utcnow() - timedelta(days=15)
        db.add(kw)
        db.commit()

        from app.api.routes.keywords import KEYWORD_READD_COOLDOWN_DAYS

        with pytest.raises(ApiError) as exc_info:
            _re_add_keyword(db, user.id, project.id, "cooldown kw")
        assert "recently deleted" in str(exc_info.value.message)

    def test_soft_deleted_keyword_can_be_readded_after_cooldown(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="free_trial")
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="readd kw")

        kw.isActive = False
        kw.deletedAt = datetime.utcnow() - timedelta(days=35)
        db.add(kw)
        db.commit()

        _re_add_keyword(db, user.id, project.id, "readd kw")
        db.commit()

        active_kw = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project.id,
                Keyword.keyword == "readd kw",
                Keyword.isActive == True,
            )
        )
        assert active_kw is not None

    def test_deactivated_keyword_can_be_readded_immediately(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine)

        user = make_user(db, plan="free_trial")
        project = make_project(db, user.id)
        kw = make_keyword(db, project.id, user.id, keyword="deactivated kw")

        kw.isActive = False
        kw.deletedAt = None
        db.add(kw)
        db.commit()

        _re_add_keyword(db, user.id, project.id, "deactivated kw")
        db.commit()

        active_kw = db.scalar(
            select(Keyword).where(
                Keyword.projectId == project.id,
                Keyword.keyword == "deactivated kw",
                Keyword.isActive == True,
            )
        )
        assert active_kw is not None


class TestRateLimiting:
    def test_login_rate_limit(self):
        from app.core.rate_limiter import _rate_limiter

        key = "login:127.0.0.1"
        for _ in range(10):
            assert _rate_limiter.is_allowed(key, 10, 60) is True
        assert _rate_limiter.is_allowed(key, 10, 60) is False

    def test_otp_rate_limit(self):
        from app.core.rate_limiter import _rate_limiter

        key = "send_otp_route:127.0.0.1"
        for _ in range(3):
            assert _rate_limiter.is_allowed(key, 3, 60) is True
        assert _rate_limiter.is_allowed(key, 3, 60) is False


def _re_add_keyword(db, user_id, project_id, keyword_text):
    """Helper to simulate re-adding a keyword."""
    from app.services.keyword_service import add_keyword
    return add_keyword(db, user_id, project_id, {
        "keyword": keyword_text,
        "location": "India",
    })
