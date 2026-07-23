from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import secrets
from hashlib import sha256

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_ACCESS_EXPIRES_IN_DAYS)
    payload = {"userId": user_id, "email": email, "exp": expires_at}
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=["HS256"])

def generate_email_verification_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
