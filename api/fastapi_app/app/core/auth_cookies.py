"""Central cookie and CSRF policy for browser authentication."""

import hmac
from hashlib import sha256

from fastapi import Request, Response

from app.core.config import get_settings


def cookie_secure() -> bool:
    return get_settings().ENV == "production"


def cookie_max_age() -> int:
    return int(get_settings().JWT_ACCESS_EXPIRES_IN_DAYS * 86400)


def csrf_for_session(session_token: str) -> str:
    secret = get_settings().JWT_ACCESS_SECRET.encode("utf-8")
    return hmac.new(secret, f"csrf:{session_token}".encode("utf-8"), sha256).hexdigest()


def set_auth_cookies(response: Response, access_token: str, session_token: str) -> None:
    settings = get_settings()
    common = {
        "secure": cookie_secure(),
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": "/",
        "max_age": cookie_max_age(),
    }
    response.set_cookie(settings.AUTH_COOKIE_NAME, access_token, httponly=True, **common)
    response.set_cookie(settings.SESSION_COOKIE_NAME, session_token, httponly=True, **common)
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_for_session(session_token),
        httponly=False,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    common = {"secure": cookie_secure(), "samesite": settings.AUTH_COOKIE_SAMESITE, "path": "/"}
    response.delete_cookie(settings.AUTH_COOKIE_NAME, httponly=True, **common)
    response.delete_cookie(settings.SESSION_COOKIE_NAME, httponly=True, **common)
    response.delete_cookie(settings.CSRF_COOKIE_NAME, httponly=False, **common)


def read_auth_cookies(request: Request) -> tuple[str | None, str | None]:
    settings = get_settings()
    return request.cookies.get(settings.AUTH_COOKIE_NAME), request.cookies.get(settings.SESSION_COOKIE_NAME)


def csrf_is_valid(request: Request) -> bool:
    settings = get_settings()
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)
    if not session_token or not cookie_token or not header_token:
        return False
    expected = csrf_for_session(session_token)
    return hmac.compare_digest(cookie_token, header_token) and hmac.compare_digest(cookie_token, expected)
