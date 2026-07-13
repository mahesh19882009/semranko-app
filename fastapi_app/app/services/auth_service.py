from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import (
    create_access_token,
    generate_email_verification_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.models import User
from app.services import email_service
from app.utils.serializers import model_to_dict


def register_user(db: Session, payload: dict) -> dict:
    settings = get_settings()

    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")

    if not name or not email or not password:
        raise ApiError(400, "Name, email and password are required")

    normalized_email = email.strip().lower()

    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise ApiError(409, "Email already registered")

    raw_token, token_hash = generate_email_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)

    user = User(
        name=name.strip(),
        email=normalized_email,
        passwordHash=hash_password(password),
        isVerified=False,
        emailVerificationToken=token_hash,
        emailVerificationExpiresAt=expires_at,
        authProvider="local",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    frontend_url = (settings.FRONTEND_URL).rstrip("/")
    verification_url = f"{frontend_url}/verify-email?token={raw_token}"

    email_service.send_verification_email(user.email, user.name, verification_url)

    return model_to_dict(
        user,
        exclude={"passwordHash", "emailVerificationToken"}
    )

def verify_email_token(db: Session, payload: dict) -> dict:
    token = payload.get("token")
    if not token:
        raise ApiError(400, "Verification token is required")

    token_hash = hash_token(token)

    user = db.scalar(select(User).where(User.emailVerificationToken == token_hash))
    if not user:
        raise ApiError(400, "Invalid verification token")

    if user.isVerified:
        return {"verified": True}

    if not user.emailVerificationExpiresAt or user.emailVerificationExpiresAt < datetime.utcnow():
        raise ApiError(400, "Verification token has expired")

    user.isVerified = True
    user.emailVerificationToken = None
    user.emailVerificationExpiresAt = None

    db.add(user)
    db.commit()

    return {"verified": True}


def resend_verification_email(db: Session, payload: dict) -> dict:
    settings = get_settings()

    email = payload.get("email")
    if not email:
        raise ApiError(400, "Email is required")

    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user:
        raise ApiError(404, "User not found")

    if user.isVerified:
        return {"sent": False, "alreadyVerified": True}

    raw_token, token_hash = generate_email_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)

    user.emailVerificationToken = token_hash
    user.emailVerificationExpiresAt = expires_at

    db.add(user)
    db.commit()

    frontend_url = settings.FRONTEND_URL.rstrip("/")
    verification_url = f"{frontend_url}/verify-email?token={raw_token}"

    email_service.send_verification_email(user.email, user.name, verification_url)

    return {"sent": True}

def login_user(db: Session, payload: dict) -> dict:
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        raise ApiError(400, "Email and password are required")

    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user:
        raise ApiError(401, "Invalid email or password")

    if not user.passwordHash or not verify_password(password, user.passwordHash):
        raise ApiError(401, "Invalid email or password")

    if not user.isVerified:
        raise ApiError(403, "Please verify your email before logging in")

    access_token = create_access_token(str(user.id), user.email)

    return {
        "accessToken": access_token,
        "user": model_to_dict(
            user,
            exclude={"passwordHash", "emailVerificationToken"}
        ),
    }