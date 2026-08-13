"""
OTP Service abstraction for mobile verification.

Uses 2Factor.in as the SMS provider.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import requests
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import User
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _normalize_mobile(mobile: str) -> str:
    """Normalize mobile number to E.164 format without leading +."""
    cleaned = re.sub(r"[^\d]", "", mobile)
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned
    if len(cleaned) == 10:
        return f"91{cleaned}"
    return cleaned


def _mask_mobile(mobile: str) -> str:
    """Mask mobile number for logging."""
    if len(mobile) >= 6:
        return f"{mobile[:2]}****{mobile[-4:]}"
    return "****"


def send_otp(db: Session, user_id: str, mobile: str) -> dict:
    """Send OTP to user's mobile number via 2Factor.in."""
    normalized = _normalize_mobile(mobile)
    
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_user = db.scalar(select(User).where(User.mobileNumber == normalized, User.id != user_id))
    if existing_user:
        raise HTTPException(status_code=409, detail="Mobile number already registered")
    
    otp_length = 6
    otp_expire_minutes = 5
    resend_cooldown_seconds = 60
    max_attempts = 3
    
    now = datetime.utcnow()
    
    if user.mobileOtpLastSentAt:
        elapsed = (now - user.mobileOtpLastSentAt).total_seconds()
        if elapsed < resend_cooldown_seconds:
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {int(resend_cooldown_seconds - elapsed)} seconds before requesting another OTP",
            )
    
    api_key = getattr(settings, "TWOFACTOR_API_KEY", None)
    if not api_key:
        raise HTTPException(status_code=500, detail="OTP service not configured")
    
    try:
        response = requests.get(
            f"https://2factor.in/API/V1/{api_key}/SMS/{normalized}/AUTOGEN/OTP",
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("Status") != "Success":
            raise HTTPException(status_code=500, detail=f"Failed to send OTP: {result.get('Message')}")
        
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
        }
    except HTTPException:
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
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one")
    
    if user.mobileOtpAttempts >= 3:
        raise HTTPException(status_code=429, detail="Maximum OTP attempts exceeded. Please request a new OTP")
    
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
            db.add(user)
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        user.mobileVerified = True
        user.mobileVerificationOtp = None
        user.mobileVerificationExpiresAt = None
        user.mobileOtpAttempts = 0
        db.add(user)
        db.commit()
        
        logger.info("Mobile verified for user=%s mobile=%s", user_id, _mask_mobile(user.mobileNumber))
        
        return {"success": True, "message": "Mobile number verified successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("OTP verification failed for user=%s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="OTP verification failed")


def resend_otp(db: Session, user_id: str) -> dict:
    """Resend OTP to user's mobile number."""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.mobileNumber:
        raise HTTPException(status_code=400, detail="Mobile number not set. Please set mobile number first")
    
    if user.mobileVerified:
        return {"success": True, "message": "Mobile number already verified"}
    
    return send_otp(db, user_id, user.mobileNumber)


def is_account_verified(db: Session, user_id: str) -> bool:
    """Check if user's account is fully verified (email + mobile)."""
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        return False
    return bool(user.isVerified and user.mobileVerified)
