"""Focused regression tests for pre-launch abuse controls."""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.core.errors import ApiError
from app.core.rate_limiter import MemoryRateLimiter
from app.services.turnstile_service import verify_turnstile


def test_memory_fallback_enforces_concurrent_limit_atomically():
    limiter = MemoryRateLimiter()
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: limiter.is_allowed("same-key", 7, 60), range(40)))
    assert sum(results) == 7


def test_turnstile_is_offline_safe_in_development_without_secret():
    settings = SimpleNamespace(ENV="development", TURNSTILE_SECRET_KEY=None)
    with patch("app.services.turnstile_service.get_settings", return_value=settings), patch(
        "app.services.turnstile_service.requests.post"
    ) as provider:
        verify_turnstile(None, "127.0.0.1", "register")
    provider.assert_not_called()


def test_turnstile_fails_closed_in_production_without_secret():
    settings = SimpleNamespace(ENV="production", TURNSTILE_SECRET_KEY=None)
    with patch("app.services.turnstile_service.get_settings", return_value=settings):
        with pytest.raises(ApiError) as exc:
            verify_turnstile(None, "203.0.113.1", "register")
    assert exc.value.status_code == 503
    assert exc.value.data["error"] == "TURNSTILE_UNAVAILABLE"


def test_turnstile_rejects_wrong_action():
    settings = SimpleNamespace(ENV="production", TURNSTILE_SECRET_KEY="test-secret")
    response = SimpleNamespace(json=lambda: {"success": True, "action": "forgot_password"})
    with patch("app.services.turnstile_service.get_settings", return_value=settings), patch(
        "app.services.turnstile_service.requests.post", return_value=response
    ):
        with pytest.raises(ApiError) as exc:
            verify_turnstile("token", "203.0.113.1", "register")
    assert exc.value.data["error"] == "TURNSTILE_REJECTED"


def test_security_sensitive_routes_are_not_client_test_mode_bypassable():
    source = (Path(__file__).parent / "fastapi_app/app/api/routes/keyword_research.py").read_text()
    assert source.count('x_test_mode == "true" and settings.ENV == "test"') == 3


def test_otp_rules_include_user_phone_ip_and_send_lock():
    source = (Path(__file__).parent / "fastapi_app/app/services/otp_service.py").read_text()
    for rule in ("otp:user-hour", "otp:user-day", "otp:phone-day", "otp:ip-hour", "otp:send-lock"):
        assert rule in source


def test_cookie_authentication_is_explicitly_documented():
    documentation = (Path(__file__).parents[1] / "SECURITY_DEPLOYMENT.md").read_text()
    assert "HttpOnly" in documentation
    assert "X-CSRF-Token" in documentation
    assert "never receive or persist" in documentation
