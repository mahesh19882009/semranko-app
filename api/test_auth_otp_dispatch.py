"""Regression coverage for registration OTP dispatch and safe provider failures."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.deps import db_session
from app.core.config import Settings
from app.core.security import create_mobile_verification_token, decode_mobile_verification_token
from app.core.errors import ApiError
from app.db.models import Base, User
from app.main import app
from app.services.auth_service import register_user
from app.services.otp_service import OTP_PROVIDER_UNAVAILABLE_MESSAGE, resend_otp, send_otp, verify_otp
from app.core.rate_limiter import _memory, _redis, _LUA
from app.core.security import decode_access_token


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    _memory._buckets.clear()
    try:
        for key in _redis.scan_iter("semranko:rate:*"):
            _redis.delete(key)
    except Exception:
        pass
    yield
    _memory._buckets.clear()
    try:
        for key in _redis.scan_iter("semranko:rate:*"):
            _redis.delete(key)
    except Exception:
        pass


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db: Session) -> User:
    user = User(
        id="otp-user",
        name="OTP User",
        email="otp-user@example.com",
        passwordHash="hash",
        selectedPlan="free_trial",
        subscriptionStatus="free",
        mobileNumber="919876543210",
        creditBalance=0,
        planCreditBalance=0,
        purchasedCreditBalance=0,
        automaticCreditBalance=0,
    )
    db.add(user)
    db.commit()
    return user


def _override_db():
    yield object()


def test_settings_declares_configured_twofactor_key_field():
    assert "TWOFACTOR_API_KEY" in Settings.model_fields


def test_register_dispatches_otp_once_and_returns_accepted_status(monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.verify_turnstile", lambda *args: None)
    monkeypatch.setattr(
        "app.api.routes.auth.register_user",
        lambda db, payload: {"id": "new-user", "mobileNumber": "919876543210", "mobileVerificationToken": "token"},
    )
    send = Mock(return_value={"masked_mobile": "+91 ••••• 3210", "expires_in_minutes": 5})
    monkeypatch.setattr("app.api.routes.auth.send_otp", send)
    app.dependency_overrides[db_session] = _override_db
    try:
        response = TestClient(app).post("/api/auth/register", json={
            "name": "New User", "email": "new@example.com", "password": "safe-password",
            "mobile": "9876543210", "mobileCountry": "IN",
        })
    finally:
        app.dependency_overrides.pop(db_session, None)

    assert response.status_code == 201
    send.assert_called_once()
    otp = response.json()["data"]["mobileOtp"]
    assert otp == {"requested": True, "maskedMobile": "+91 ••••• 3210", "expiresInMinutes": 5}


def test_register_preserves_account_success_when_otp_provider_is_unavailable(monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.verify_turnstile", lambda *args: None)
    monkeypatch.setattr(
        "app.api.routes.auth.register_user",
        lambda db, payload: {"id": "new-user", "mobileNumber": "919876543210", "mobileVerificationToken": "token"},
    )
    monkeypatch.setattr(
        "app.api.routes.auth.send_otp",
        lambda *args, **kwargs: (_ for _ in ()).throw(ApiError(
            503, OTP_PROVIDER_UNAVAILABLE_MESSAGE, {"error": "OTP_PROVIDER_UNAVAILABLE"}
        )),
    )
    app.dependency_overrides[db_session] = _override_db
    try:
        response = TestClient(app).post("/api/auth/register", json={
            "name": "New User", "email": "new@example.com", "password": "safe-password",
            "mobile": "9876543210", "mobileCountry": "IN",
        })
    finally:
        app.dependency_overrides.pop(db_session, None)

    assert response.status_code == 201
    otp = response.json()["data"]["mobileOtp"]
    assert otp["requested"] is False
    assert otp["error"] == "OTP_PROVIDER_UNAVAILABLE"
    assert otp["message"] == OTP_PROVIDER_UNAVAILABLE_MESSAGE


def test_unconfigured_or_malformed_provider_send_is_structured_and_safe():
    db = _db()
    user = _user(db)

    with patch("app.services.otp_service.settings") as settings:
        settings.TWOFACTOR_API_KEY = None
        with pytest.raises(ApiError) as error:
            send_otp(db, user.id, "9876543210", country="IN")
    assert error.value.status_code == 503
    assert error.value.data["error"] == "OTP_PROVIDER_UNAVAILABLE"
    assert error.value.message == OTP_PROVIDER_UNAVAILABLE_MESSAGE

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = request_get.return_value
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Success"}
        with pytest.raises(ApiError) as error:
            send_otp(db, user.id, "9876543210", country="IN")
    assert error.value.status_code == 502
    assert error.value.data["error"] == "OTP_PROVIDER_INVALID_RESPONSE"
    assert error.value.message == OTP_PROVIDER_UNAVAILABLE_MESSAGE

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = request_get.return_value
        response.raise_for_status.return_value = None
        response.json.return_value = []
        with pytest.raises(ApiError) as error:
            send_otp(db, user.id, "9876543210", country="IN")
    assert error.value.status_code == 502
    assert error.value.data["error"] == "OTP_PROVIDER_INVALID_RESPONSE"


def test_registration_persists_subject_and_its_token_can_securely_resend_after_initial_provider_failure():
    db = _db()

    class NoopThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    with patch("app.services.auth_service.threading.Thread", NoopThread):
        registration = register_user(db, {
            "name": "Recovery User",
            "email": "recovery@example.com",
            "password": "safe-password",
            "mobile": "7051282603",
            "mobileCountry": "IN",
        })

    subject = decode_mobile_verification_token(registration["mobileVerificationToken"])
    assert subject == registration["id"]
    assert db.get(User, subject) is not None

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Success", "Details": "recovery-session"}
        request_get.return_value = response
        result = resend_otp(db, subject)

    assert result["success"] is True
    assert "/SMS/917051282603/AUTOGEN/OTP" in request_get.call_args.args[0]
    db.refresh(db.get(User, subject))
    assert db.get(User, subject).mobileVerificationOtp == "recovery-session"

    from app.api.deps import db_session

    def override_db():
        yield db

    resend = Mock(return_value={"success": True, "masked_mobile": "+91 ••••• 2603"})
    app.dependency_overrides[db_session] = override_db
    with patch("app.api.routes.auth.verify_turnstile", lambda *args: None), patch(
        "app.api.routes.auth.resend_otp_service", resend
    ):
        try:
            response = TestClient(app).post("/api/auth/resend-otp", json={
                "verificationToken": registration["mobileVerificationToken"],
            })
        finally:
            app.dependency_overrides.pop(db_session, None)
    assert response.status_code == 200
    assert response.json()["data"]["success"] is True
    assert resend.call_args.args[1] == subject


def test_missing_or_invalid_mobile_verification_subject_is_structured_and_enumeration_safe():
    db = _db()
    with pytest.raises(ApiError) as error:
        resend_otp(db, "missing-user")
    assert error.value.status_code == 401
    assert error.value.data == {
        "error": "MOBILE_VERIFICATION_SESSION_EXPIRED", "action": "login",
    }

    from app.api.deps import db_session

    def override_db():
        yield db

    app.dependency_overrides[db_session] = override_db
    try:
        response = TestClient(app).post("/api/auth/resend-otp", json={
            "verificationToken": "not-a-mobile-verification-token",
        })
    finally:
        app.dependency_overrides.pop(db_session, None)
    assert response.status_code == 401
    payload = response.json()
    assert payload["data"]["error"] == "MOBILE_VERIFICATION_SESSION_EXPIRED"


def test_verify_otp_accepts_provider_success_with_correct_casing():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
    db.add(user)
    db.commit()

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Success", "Details": "OTP Matched"}
        request_get.return_value = response

        result = verify_otp(db, user.id, "123456")
        assert result["success"] is True

    db.refresh(user)
    assert user.mobileVerified is True
    assert user.mobileVerificationOtp is None
    assert request_get.call_args.args[0] == f"https://2factor.in/API/V1/test-key/SMS/VERIFY/session-A/123456"


def test_verify_otp_rejects_invalid_otp_and_exhausts_attempts():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
    user.mobileOtpAttempts = 0
    db.add(user)
    db.commit()

    for _ in range(3):
        with patch("app.services.otp_service.settings") as settings, patch(
            "app.services.otp_service.requests.get"
        ) as request_get:
            settings.TWOFACTOR_API_KEY = "test-key"
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"Status": "Success", "Details": "Invalid OTP"}
            request_get.return_value = response

            with pytest.raises(ApiError) as exc_info:
                verify_otp(db, user.id, "000000")
            assert exc_info.value.status_code == 400
            assert exc_info.value.data["error"] == "OTP_INVALID"

        db.refresh(user)

    assert user.mobileOtpAttempts == 3
    assert user.mobileVerificationOtp is None
    assert user.mobileVerificationExpiresAt is None

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Success", "Details": "Invalid OTP"}
        request_get.return_value = response

        with pytest.raises(ApiError) as exc_info:
            verify_otp(db, user.id, "000000")
        assert exc_info.value.status_code == 400
        assert exc_info.value.data["error"] == "OTP_EXPIRED"


def test_verify_otp_rejects_expired_session():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() - timedelta(minutes=1)
    db.add(user)
    db.commit()

    with pytest.raises(ApiError) as exc_info:
        verify_otp(db, user.id, "123456")
    assert exc_info.value.status_code == 400
    assert exc_info.value.data["error"] == "OTP_EXPIRED"


def test_verify_otp_uses_newest_session_after_resend():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
    db.add(user)
    db.commit()

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Success", "Details": "session-B"}
        request_get.return_value = response

        result = send_otp(db, user.id, "919876543210")
        assert result["session_id"] == "session-B"

    db.refresh(user)
    assert user.mobileVerificationOtp == "session-B"

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Success", "Details": "OTP Matched"}
        request_get.return_value = response

        result = verify_otp(db, user.id, "654321")
        assert result["success"] is True

    assert request_get.call_args.args[0] == "https://2factor.in/API/V1/test-key/SMS/VERIFY/session-B/654321"
    assert "session-A" not in request_get.call_args.args[0]


def test_verify_otp_handles_provider_business_rejection():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
    db.add(user)
    db.commit()

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"Status": "Failure", "Details": "Your OTP has expired"}
        request_get.return_value = response

        with pytest.raises(ApiError) as exc_info:
            verify_otp(db, user.id, "123456")
        assert exc_info.value.status_code == 400
        assert exc_info.value.data["error"] == "OTP_INVALID"


def test_verify_otp_handles_malformed_provider_response():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
    db.add(user)
    db.commit()

    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        request_get.return_value = response

        with pytest.raises(ApiError) as exc_info:
            verify_otp(db, user.id, "123456")
        assert exc_info.value.status_code == 400
        assert exc_info.value.data["error"] == "OTP_INVALID"


def test_verify_otp_network_failure_does_not_consume_attempt():
    db = _db()
    user = _user(db)
    user.mobileNumber = "919876543210"
    user.mobileVerificationOtp = "session-A"
    user.mobileVerificationExpiresAt = datetime.utcnow() + timedelta(minutes=5)
    user.mobileOtpAttempts = 1
    db.add(user)
    db.commit()

    import requests
    with patch("app.services.otp_service.settings") as settings, patch(
        "app.services.otp_service.requests.get"
    ) as request_get:
        settings.TWOFACTOR_API_KEY = "test-key"
        request_get.side_effect = requests.ConnectionError("Network failure")

        with pytest.raises(ApiError) as exc_info:
            verify_otp(db, user.id, "123456")
        assert exc_info.value.status_code == 503
        assert exc_info.value.data["error"] == "OTP_PROVIDER_UNAVAILABLE"

    db.refresh(user)
    assert user.mobileOtpAttempts == 1


def test_verify_otp_purpose_token_cannot_authenticate_normal_apis():
    from app.core.security import create_mobile_verification_token

    token = create_mobile_verification_token("user-123")
    payload = decode_access_token(token)
    assert payload.get("purpose") == "mobile_verification"

    from app.api.deps import get_current_user

    with pytest.raises(Exception):
        get_current_user(token)

