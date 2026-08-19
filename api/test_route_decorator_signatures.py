"""Regression coverage for FastAPI-compatible custom route decorators."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.main import app
from app.core.security import create_mobile_verification_token, decode_mobile_verification_token, decode_access_token


def _parameter_names(operation: dict) -> set[str]:
    return {parameter["name"] for parameter in operation.get("parameters", [])}


def test_mobile_verification_token_is_scoped_and_short_lived():
    token = create_mobile_verification_token("user-1")
    assert decode_mobile_verification_token(token) == "user-1"
    payload = decode_access_token(token)
    assert payload["purpose"] == "mobile_verification"
    assert payload["userId"] == "user-1"


def test_openapi_never_exposes_decorator_args_or_kwargs():
    schema = app.openapi()

    leaked = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            invalid = _parameter_names(operation) & {"args", "kwargs"}
            if invalid:
                leaked.append((method.upper(), path, sorted(invalid)))

    assert leaked == []


def test_login_accepts_body_without_fake_decorator_query_parameters(monkeypatch):
    class FakeDb:
        pass

    def override_db_session():
        yield FakeDb()

    monkeypatch.setattr(
        "app.api.routes.auth.login_user",
        lambda db, payload: {
            "user": {"id": "user-1", "email": payload["email"]},
            "accessToken": "access-token",
        },
    )
    monkeypatch.setattr("app.api.routes.auth.invalidate_session", lambda user_id: None)
    monkeypatch.setattr("app.api.routes.auth.generate_session_token", lambda: "session-token")
    monkeypatch.setattr("app.api.routes.auth.store_session", lambda user_id, token: None)
    app.dependency_overrides[db_session] = override_db_session

    try:
        response = TestClient(app).post(
            "/api/auth/login",
            json={"email": "person@example.com", "password": "correct-password"},
        )
    finally:
        app.dependency_overrides.pop(db_session, None)

    assert response.status_code == 200
    assert "sessionToken" not in response.json()["data"]
    assert "accessToken" not in response.json()["data"]
    cookies = response.headers.get_list("set-cookie")
    assert any("semranko_access=" in cookie and "HttpOnly" in cookie for cookie in cookies)
    assert any("semranko_session=" in cookie and "HttpOnly" in cookie for cookie in cookies)


def test_all_rate_limited_auth_routes_keep_declared_request_shapes():
    schema = app.openapi()
    expected_body_routes = {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/mobile-verification-session",
        "/api/auth/resend-verification",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/send-otp",
        "/api/auth/verify-otp",
    }

    for path in expected_body_routes:
        operation = schema["paths"][path]["post"]
        assert "requestBody" in operation
        assert "args" not in _parameter_names(operation)
        assert "kwargs" not in _parameter_names(operation)

    resend_operation = schema["paths"]["/api/auth/resend-otp"]["post"]
    assert "requestBody" in resend_operation
    assert "args" not in _parameter_names(resend_operation)
    assert "kwargs" not in _parameter_names(resend_operation)
