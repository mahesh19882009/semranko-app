"""
OTP Service abstraction for mobile verification.

Uses 2Factor.in as the SMS provider.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import User
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.rate_limiter import consume_limit
from app.services.phone_number_service import (
    mask_phone_number,
    normalize_phone_number,
    to_provider_phone_number,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _normalize_mobile(mobile: str, country: str | None = None) -> str:
    """Backward-compatible gateway to canonical country-aware normalization."""
    return normalize_phone_number(mobile, country)


def _mask_mobile(mobile: str) -> str:
    """Mask mobile number for logging."""
    return mask_phone_number(mobile)


def _enforce_send_limits(user_id: str, mobile: str, source_ip: str | None) -> None:
    checks = (
        (f"otp:user-hour:{user_id}", 3, 3600),
        (f"otp:user-day:{user_id}", 5, 86400),
        (f"otp:phone-day:{mobile}", 5, 86400),
        (f"otp:ip-hour:{source_ip or 'unknown'}", 10, 3600),
        (f"otp:send-lock:{user_id}", 1, 10),
    )
    for key, limit, window in checks:
        allowed, retry_after = consume_limit(key, limit, window)
        if not allowed:
            logger.warning("OTP send throttled user=%s rule=%s", user_id, key.split(":")[1])
            raise ApiError(429, "Too many OTP requests. Please try again later", {
                "error": "OTP_SEND_LIMIT_EXCEEDED", "retryAfter": retry_after,
            })


def send_otp(
    db: Session,
    user_id: str,
    mobile: str,
    source_ip: str | None = None,
    country: str | None = None,
) -> dict:
    """Send OTP to user's mobile number via 2Factor.in."""
    normalized = _normalize_mobile(mobile, country)
    
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_user = db.scalar(select(User).where(User.mobileNumber == normalized, User.id != user_id))
    if existing_user:
        raise HTTPException(status_code=409, detail="Mobile number already registered")

    if source_ip is not None:
        _enforce_send_limits(user_id, normalized, source_ip)
    
    otp_length = 6
    otp_expire_minutes = 5
    resend_cooldown_seconds = 60
    max_attempts = 3
    
    now = datetime.utcnow()
    
    if user.mobileOtpLastSentAt:
        elapsed = (now - user.mobileOtpLastSentAt).total_seconds()
        if elapsed < resend_cooldown_seconds:
            retry_after = int(resend_cooldown_seconds - elapsed)
            raise ApiError(429, f"Please wait {retry_after} seconds before requesting another OTP", {
                "error": "OTP_RESEND_COOLDOWN", "retryAfter": retry_after,
            })
    
    api_key = getattr(settings, "TWOFACTOR_API_KEY", None)
    if not api_key:
        raise HTTPException(status_code=500, detail="OTP service not configured")
    
    try:
        provider_mobile = to_provider_phone_number(normalized)
        response = requests.get(
            f"https://2factor.in/API/V1/{api_key}/SMS/{provider_mobile}/AUTOGEN/OTP",
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("Status") != "Success":
            logger.warning("OTP provider rejected send user=%s", user_id)
            raise HTTPException(status_code=502, detail="OTP provider could not send the message")
        
        user.mobileNumber = normalized
        user.mobileVerificationOtp = str(result.get("SessionId", ""))
        user.mobileVerificationExpiresAt = now + timedelta(minutes=otp_expire_minutes)
        user.mobileOtpAttempts = 0
        user.mobileOtpLastSentAt = now
        db.add(user)
        db.commit()
        
        logger.info("OTP sent to user=%s mobile=%s", user_id, _mask_mobile(normalized))
        
        return {
            "success": True,
            "message": "OTP sent successfully",
            "session_id": result.get("SessionId"),
            "expires_in_minutes": otp_expire_minutes,
            "masked_mobile": _mask_mobile(normalized),
        }
    except (HTTPException, ApiError):
        raise
    except Exception as exc:
        logger.error("Failed to send OTP to user=%s mobile=%s: %s", user_id, _mask_mobile(normalized), exc)
        raise HTTPException(status_code=500, detail="Failed to send OTP")


def verify_otp(db: Session, user_id: str, otp: str) -> dict:
    """Verify OTP for user's mobile number."""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.mobileNumber:
        raise HTTPException(status_code=400, detail="Mobile number not found. Please request OTP first")
    
    if not user.mobileVerificationExpiresAt or user.mobileVerificationExpiresAt < datetime.utcnow():
        raise ApiError(400, "OTP has expired. Please request a new one", {
            "error": "OTP_EXPIRED", "action": "resend_otp",
        })
    
    if user.mobileOtpAttempts >= 3:
        raise ApiError(429, "Maximum OTP attempts exceeded. Please request a new OTP", {
            "error": "OTP_ATTEMPTS_EXCEEDED", "action": "resend_otp",
        })
    
    api_key = getattr(settings, "TWOFACTOR_API_KEY", None)
    if not api_key:
        raise HTTPException(status_code=500, detail="OTP service not configured")
    
    try:
        response = requests.get(
            f"https://2factor.in/API/V1/{api_key}/SMS/VERIFY/{user.mobileVerificationOtp}/{otp}",
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("Status") != "Success" or result.get("Details") != "OTP matched":
            user.mobileOtpAttempts += 1
            if user.mobileOtpAttempts >= 3:
                user.mobileVerificationOtp = None
                user.mobileVerificationExpiresAt = None
            db.add(user)
            db.commit()
            raise ApiError(400, "Invalid OTP", {"error": "OTP_INVALID"})
        
        user.mobileVerified = True
        user.mobileVerificationOtp = None
        user.mobileVerificationExpiresAt = None
        user.mobileOtpAttempts = 0
        db.add(user)
        db.commit()
        
        logger.info("Mobile verified for user=%s mobile=%s", user_id, _mask_mobile(user.mobileNumber))
        
        return {"success": True, "message": "Mobile number verified successfully"}
    except (HTTPException, ApiError):
        raise
    except Exception as exc:
        logger.error("OTP verification failed for user=%s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="OTP verification failed")


def resend_otp(db: Session, user_id: str, source_ip: str | None = None) -> dict:
    """Resend OTP to user's mobile number."""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.mobileNumber:
        raise HTTPException(status_code=400, detail="Mobile number not set. Please set mobile number first")
    
    if user.mobileVerified:
        return {"success": True, "message": "Mobile number already verified"}
    
    return send_otp(db, user_id, user.mobileNumber, source_ip=source_ip)


def is_account_verified(db: Session, user_id: str) -> bool:
    """Check if user's account is fully verified (email + mobile)."""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        return False
    return bool(user.isVerified and user.mobileVerified)
