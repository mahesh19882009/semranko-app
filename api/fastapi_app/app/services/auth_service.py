from datetime import datetime, timedelta
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import (
    create_mobile_verification_token,
    generate_email_verification_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.models import User
from app.services import email_service
from app.services.otp_service import _normalize_mobile
from app.services.phone_number_service import mask_phone_number
from app.utils.serializers import model_to_dict
from app.core.session import invalidate_session


def _send_verification_email_background(email, name, verification_url):
    try:
        email_service.send_verification_email(email, name, verification_url)
    except Exception:
        pass


def register_user(db: Session, payload: dict) -> dict:
    settings = get_settings()

    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")
    mobile = payload.get("mobile")

    if not name or not email or not password or not mobile:
        raise ApiError(400, "Name, email, mobile and password are required")

    normalized_email = email.strip().lower()
    normalized_mobile = _normalize_mobile(mobile, payload.get("mobileCountry"))

    existing_email = db.scalar(select(User).where(User.email == normalized_email))
    if existing_email:
        raise ApiError(409, "Email already registered")

    existing_mobile = db.scalar(select(User).where(User.mobileNumber == normalized_mobile))
    if existing_mobile:
        raise ApiError(409, "Mobile number already registered")

    raw_token, token_hash = generate_email_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)

    free_started_at = datetime.utcnow()

    user = User(
        name=name.strip(),
        email=normalized_email,
        passwordHash=hash_password(password),
        isVerified=False,
        emailVerificationToken=token_hash,
        emailVerificationExpiresAt=expires_at,
        authProvider="local",
        selectedPlan="free_trial",
        subscriptionStatus="free",
        trialStartsAt=None,
        trialEndsAt=None,
        planAnniversaryAt=free_started_at,
        lastCreditResetAt=free_started_at,
        creditBalance=100.0,
        planCreditBalance=100.0,
        purchasedCreditBalance=0.0,
        automaticCreditBalance=0.0,
        mobileNumber=normalized_mobile,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
    verification_url = f"{frontend_url}/verify-email?token={raw_token}"

    email_thread = threading.Thread(
        target=_send_verification_email_background,
        args=(user.email, user.name, verification_url),
        daemon=True,
    )
    email_thread.start()

    result = model_to_dict(
        user,
        exclude={"passwordHash", "emailVerificationToken"}
    )
    result["emailSent"] = True
    result["mobileVerificationRequired"] = True
    result["mobileVerificationToken"] = create_mobile_verification_token(user.id)
    result["mobileMasked"] = mask_phone_number(normalized_mobile)
    return result


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
        return {"sent": True}

    if user.isVerified:
        return {"sent": True}

    raw_token, token_hash = generate_email_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)

    user.emailVerificationToken = token_hash
    user.emailVerificationExpiresAt = expires_at

    db.add(user)
    db.commit()

    frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
    verification_url = f"{frontend_url}/verify-email?token={raw_token}"

    email_sent = email_service.send_verification_email(user.email, user.name, verification_url)

    return {"sent": email_sent}


def login_user(db: Session, payload: dict) -> dict:
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        raise ApiError(400, "Email and password are required")

    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user:
        raise ApiError(401, "Invalid email or password", {"error": "INVALID_CREDENTIALS"})

    if not user.passwordHash or not verify_password(password, user.passwordHash):
        raise ApiError(401, "Invalid email or password", {"error": "INVALID_CREDENTIALS"})

    if not user.isVerified:
        raise ApiError(403, "Please verify your email before logging in", {
            "error": "EMAIL_VERIFICATION_REQUIRED",
            "action": "resend_verification",
        })

    if not user.mobileVerified:
        raise ApiError(403, "Please verify your mobile number before logging in", {
            "error": "MOBILE_VERIFICATION_REQUIRED",
            "action": "verify_mobile",
        })

    return {
        "user": model_to_dict(
            user,
            exclude={"passwordHash", "emailVerificationToken"}
        ),
    }


def create_mobile_verification_session(db: Session, payload: dict) -> dict:
    email = str(payload.get("email") or "").strip().lower()
    password = payload.get("password")
    if not email or not password:
        raise ApiError(400, "Email and password are required")
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.passwordHash or not verify_password(password, user.passwordHash):
        raise ApiError(401, "Invalid email or password", {"error": "INVALID_CREDENTIALS"})
    if user.mobileVerified:
        return {"mobileVerified": True}
    return {
        "mobileVerified": False,
        "mobileVerificationToken": create_mobile_verification_token(user.id),
        "mobileMasked": mask_phone_number(user.mobileNumber),
    }


def forgot_password(db: Session, payload: dict) -> dict:
    settings = get_settings()

    email = payload.get("email")
    if not email:
        raise ApiError(400, "Email is required")

    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))
    if not user:
        # Return success even if user doesn't exist to prevent email enumeration
        return {"sent": True}

    if user.authProvider != "local":
        return {"sent": True}

    raw_token, token_hash = generate_email_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS)

    user.passwordResetToken = token_hash
    user.passwordResetExpiresAt = expires_at

    db.add(user)
    db.commit()

    frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"

    email_sent = email_service.send_password_reset_email(user.email, user.name, reset_url)

    return {"sent": email_sent}


def reset_password(db: Session, payload: dict) -> dict:
    token = payload.get("token")
    new_password = payload.get("newPassword")

    if not token or not new_password:
        raise ApiError(400, "Token and new password are required")

    if len(new_password) < 8:
        raise ApiError(400, "Password must be at least 8 characters long")

    token_hash = hash_token(token)

    user = db.scalar(select(User).where(User.passwordResetToken == token_hash))
    if not user:
        raise ApiError(400, "Invalid or expired reset token")

    if not user.passwordResetExpiresAt or user.passwordResetExpiresAt < datetime.utcnow():
        raise ApiError(400, "Reset token has expired")

    user.passwordHash = hash_password(new_password)
    user.passwordResetToken = None
    user.passwordResetExpiresAt = None

    db.add(user)
    db.commit()

    try:
        invalidate_session(str(user.id))
    except Exception:
        pass

    return {"reset": True}


def change_user_password(db: Session, user_id: str, current_password: str, new_password: str) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")

    if user.authProvider != "local":
        raise ApiError(400, "Password change is only available for local accounts")

    if not user.passwordHash or not verify_password(current_password, user.passwordHash):
        raise ApiError(400, "Current password is incorrect")

    if len(new_password) < 8:
        raise ApiError(400, "New password must be at least 8 characters long")

    user.passwordHash = hash_password(new_password)
    db.add(user)
    db.commit()

    try:
        invalidate_session(str(user.id))
    except Exception:
        pass

    return {"changed": True}
