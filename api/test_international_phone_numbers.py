"""Regression coverage for country-aware registration and mobile verification."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.core.errors import ApiError
from app.db.models import Base, User
from app.services.auth_service import create_mobile_verification_session, register_user
from app.services.otp_service import _enforce_send_limits, _normalize_mobile, resend_otp, send_otp
from app.services.phone_number_service import mask_phone_number, normalize_phone_number, to_provider_phone_number


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(db: Session, user_id: str, email: str, mobile: str | None = None) -> User:
    now = datetime.utcnow()
    user = User(
        id=user_id,
        name="Phone Test",
        email=email,
        passwordHash="hash",
        selectedPlan="free_trial",
        subscriptionStatus="free",
        creditBalance=100.0,
        mobileNumber=mobile,
        isVerified=True,
        mobileVerified=False,
        createdAt=now,
        updatedAt=now,
    )
    db.add(user)
    db.commit()
    return user


def _provider_success():
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"Status": "Success", "SessionId": "phone-session"}
    return response


class TestInternationalPhoneNormalization:
    def test_india_defaults_and_equivalent_formats_share_one_canonical_value(self):
        expected = "919876543210"
        assert normalize_phone_number("9876543210", "IN") == expected
        assert normalize_phone_number("+91 98765-43210", "IN") == expected
        assert normalize_phone_number("91 98765 43210", "IN") == expected
        # Legacy stored digits-only values remain valid without a selected country.
        assert normalize_phone_number(expected) == expected

    def test_international_number_uses_selected_country(self):
        assert normalize_phone_number("+1 415 555 2671", "US") == "14155552671"
        assert normalize_phone_number("14155552671", "US") == "14155552671"

    @pytest.mark.parametrize("mobile,country", [
        ("12345", "IN"),
        ("+1 415 555 2671", "IN"),
        ("not a number", "IN"),
        ("9876543210", "ZZ"),
    ])
    def test_invalid_or_country_mismatched_input_returns_structured_error(self, mobile, country):
        with pytest.raises(ApiError) as error:
            normalize_phone_number(mobile, country)
        assert error.value.status_code == 422
        assert error.value.data["error"] == "INVALID_MOBILE_NUMBER"
        assert "mobile" in error.value.data["fieldErrors"]

    def test_masked_display_keeps_only_country_code_and_last_four_digits(self):
        assert mask_phone_number("919876543210") == "+91 ••••• 3210"
        assert mask_phone_number("14155552671") == "+1 ••••• 2671"


class TestRegistrationAndOtpCompatibility:
    def test_registration_rejects_equivalent_existing_mobile_representation(self):
        db = _db()
        _user(db, "existing", "existing@example.com", mobile="919876543210")

        with pytest.raises(ApiError) as error:
            register_user(db, {
                "name": "New User",
                "email": "new@example.com",
                "password": "safe-password",
                "mobile": "+91 98765-43210",
                "mobileCountry": "IN",
            })

        assert error.value.status_code == 409
        assert error.value.message == "Mobile number already registered"

    def test_existing_digits_only_number_can_start_mobile_recovery(self):
        db = _db()
        user = _user(db, "legacy", "legacy@example.com", mobile="919876543210")

        with patch("app.services.auth_service.verify_password", return_value=True):
            result = create_mobile_verification_session(db, {
                "email": user.email,
                "password": "safe-password",
            })

        assert result["mobileVerified"] is False
        assert result["mobileMasked"] == "+91 ••••• 3210"

    def test_provider_receives_canonical_digits_only_number(self):
        db = _db()
        user = _user(db, "provider", "provider@example.com")
        with patch("app.services.otp_service.requests.get", return_value=_provider_success()) as request_get:
            with patch("app.services.otp_service.settings") as settings:
                settings.TWOFACTOR_API_KEY = "test-key"
                result = send_otp(db, user.id, "+1 415 555 2671", country="US")

        assert to_provider_phone_number("14155552671") == "14155552671"
        assert "/SMS/14155552671/AUTOGEN/OTP" in request_get.call_args.args[0]
        assert result["masked_mobile"] == "+1 ••••• 2671"

    def test_legacy_number_resend_uses_existing_canonical_digits(self):
        db = _db()
        user = _user(db, "legacy-resend", "legacy-resend@example.com", mobile="919876543210")
        user.mobileOtpLastSentAt = datetime.utcnow() - timedelta(seconds=61)
        db.add(user)
        db.commit()

        with patch("app.services.otp_service.requests.get", return_value=_provider_success()) as request_get:
            with patch("app.services.otp_service.settings") as settings:
                settings.TWOFACTOR_API_KEY = "test-key"
                result = resend_otp(db, user.id)

        assert result["success"] is True
        assert "/SMS/919876543210/AUTOGEN/OTP" in request_get.call_args.args[0]

    def test_equivalent_mobile_formats_share_the_same_otp_rate_limit_key(self):
        seen_keys = []

        def consume(key, _limit, _window):
            seen_keys.append(key)
            return True, 60

        with patch("app.services.otp_service.consume_limit", side_effect=consume):
            for raw in ("9876543210", "+91 98765-43210"):
                _enforce_send_limits("user-1", _normalize_mobile(raw, "IN"), "127.0.0.1")

        phone_keys = [key for key in seen_keys if key.startswith("otp:phone-day:")]
        assert phone_keys == ["otp:phone-day:919876543210", "otp:phone-day:919876543210"]
