"""Cloudflare Turnstile verification for public abuse-sensitive actions."""

import logging
import requests

from app.core.config import get_settings
from app.core.errors import ApiError

logger = logging.getLogger(__name__)


def verify_turnstile(token: str | None, remote_ip: str | None, expected_action: str) -> None:
    settings = get_settings()
    secret = settings.TURNSTILE_SECRET_KEY
    if not secret:
        if settings.ENV == "production":
            raise ApiError(503, "Security verification is unavailable", {"error": "TURNSTILE_UNAVAILABLE"})
        return
    if not token:
        raise ApiError(400, "Complete the security check to continue", {"error": "TURNSTILE_REQUIRED"})
    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token, "remoteip": remote_ip or ""},
            timeout=5,
        )
        result = response.json()
    except Exception as exc:
        logger.warning("Turnstile verification unavailable: %s", type(exc).__name__)
        raise ApiError(503, "Security verification is unavailable", {"error": "TURNSTILE_UNAVAILABLE"}) from exc
    action = result.get("action")
    if not result.get("success") or (action and action != expected_action):
        logger.warning("Turnstile rejected action=%s", expected_action)
        raise ApiError(400, "Security check failed. Please try again", {"error": "TURNSTILE_REJECTED"})
