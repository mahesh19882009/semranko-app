"""Security regression coverage for cookie authentication and CSRF."""

import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent / "fastapi_app"))

from app.api.deps import db_session, get_current_user
from app.core.auth_cookies import csrf_for_session, set_auth_cookies
from app.core.errors import register_exception_handlers
from app.core.security import create_access_token, create_mobile_verification_token
from app.db.session import get_db
from app.db.models import Base, User
from app.main import app
from app.services.auth_service import reset_password
from app.core.security import hash_token
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


class FakeDb:
    def scalar(self, *_args, **_kwargs):
        return None


def _login_client(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.auth.login_user",
        lambda db, payload: {"user": {"id": "user-cookie", "email": payload["email"], "name": "Cookie User"}},
    )
    monkeypatch.setattr("app.api.routes.auth.invalidate_session", lambda user_id: None)
    monkeypatch.setattr("app.api.routes.auth.generate_session_token", lambda: "server-session")
    monkeypatch.setattr("app.api.routes.auth.store_session", lambda user_id, token: None)
    app.dependency_overrides[db_session] = lambda: FakeDb()
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"email": "cookie@example.com", "password": "correct"})
    app.dependency_overrides.pop(db_session, None)
    assert response.status_code == 200
    return client, response


def test_login_sets_httponly_credentials_and_safe_response(monkeypatch):
    client, response = _login_client(monkeypatch)
    body = response.json()["data"]
    assert "accessToken" not in body and "sessionToken" not in body
    cookies = response.headers.get_list("set-cookie")
    assert any("semranko_access=" in value and "HttpOnly" in value and "SameSite=lax" in value for value in cookies)
    assert any("semranko_session=" in value and "HttpOnly" in value for value in cookies)
    assert any("semranko_csrf=" in value and "HttpOnly" not in value for value in cookies)


def test_production_auth_cookies_are_secure(monkeypatch):
    response = SimpleNamespace(set_cookie=lambda *args, **kwargs: calls.append((args, kwargs)))
    calls = []
    monkeypatch.setattr("app.core.auth_cookies.cookie_secure", lambda: True)
    set_auth_cookies(response, "access", "session")
    assert calls and all(kwargs["secure"] is True for _, kwargs in calls)


def test_authenticated_mutation_requires_valid_csrf(monkeypatch):
    client, _ = _login_client(monkeypatch)
    invalidated = []
    monkeypatch.setattr("app.api.routes.auth.invalidate_session", invalidated.append)
    missing = client.post("/api/auth/logout")
    assert missing.status_code == 403
    assert missing.json()["data"]["error"] == "CSRF_INVALID"
    invalid = client.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"})
    assert invalid.status_code == 403
    csrf = client.cookies.get("semranko_csrf")
    valid = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert valid.status_code == 200
    assert invalidated == ["user-cookie"]
    cleared = valid.headers.get_list("set-cookie")
    assert sum("Max-Age=0" in value for value in cleared) >= 3


def test_cookie_authenticated_get_and_revoked_session(monkeypatch):
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/private")
    def private(user=Depends(get_current_user)):
        return {"id": user["id"]}

    user = SimpleNamespace(
        id="user-cookie", selectedPlan="starter", subscriptionStatus="active",
        trialEndsAt=None, creditBalance=10, automaticCreditBalance=10,
    )
    fake_db = SimpleNamespace(scalar=lambda *_args, **_kwargs: user)
    mini.dependency_overrides[get_db] = lambda: fake_db
    client = TestClient(mini)
    client.cookies.set("semranko_access", create_access_token(user.id, "cookie@example.com"))
    client.cookies.set("semranko_session", "server-session")
    monkeypatch.setattr("app.api.deps.validate_session", lambda user_id, token: token == "server-session")
    assert client.get("/private").status_code == 200
    monkeypatch.setattr("app.api.deps.validate_session", lambda user_id, token: False)
    assert client.get("/private").status_code == 401


def test_revoked_browser_session_returns_unauthorized_and_clears_cookies(monkeypatch):
    client = TestClient(app)
    client.cookies.set("semranko_access", create_access_token("revoked-user", "revoked@example.com"))
    client.cookies.set("semranko_session", "revoked-session")
    client.cookies.set("semranko_csrf", csrf_for_session("revoked-session"))
    monkeypatch.setattr("app.api.deps.validate_session", lambda *_args: False)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    cleared = response.headers.get_list("set-cookie")
    assert sum("Max-Age=0" in value for value in cleared) >= 3


def test_mobile_verification_token_cannot_authenticate(monkeypatch):
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/private")
    def private(user=Depends(get_current_user)):
        return user

    mini.dependency_overrides[get_db] = lambda: FakeDb()
    client = TestClient(mini)
    client.cookies.set("semranko_access", create_mobile_verification_token("user-cookie"))
    client.cookies.set("semranko_session", "server-session")
    monkeypatch.setattr("app.api.deps.validate_session", lambda *_args: True)
    assert client.get("/private").status_code == 401


def test_password_reset_invalidates_old_server_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        id="reset-user", name="Reset", email="reset@example.com", passwordHash="old",
        passwordResetToken=hash_token("one-use-token"),
        passwordResetExpiresAt=datetime.utcnow() + timedelta(minutes=10),
        isVerified=True, mobileVerified=True,
    )
    db.add(user)
    db.commit()
    invalidated = []
    monkeypatch.setattr("app.services.auth_service.hash_password", lambda value: "new-hash")
    monkeypatch.setattr("app.services.auth_service.invalidate_session", invalidated.append)
    reset_password(db, {"token": "one-use-token", "newPassword": "new-password"})
    assert invalidated == ["reset-user"]
    assert user.passwordResetToken is None


def test_unapproved_cross_origin_is_not_credentialed():
    response = TestClient(app).options(
        "/api/auth/me",
        headers={
            "Origin": "https://attacker.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "https://attacker.invalid"
