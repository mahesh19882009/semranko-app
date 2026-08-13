from datetime import datetime, timedelta, timezone
from typing import Optional
from functools import wraps

import bcrypt
import jwt
import secrets
from hashlib import sha256
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import User
from app.core.auth_cookies import read_auth_cookies
from app.core.session import validate_session


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_ACCESS_EXPIRES_IN_DAYS)
    payload = {"userId": user_id, "email": email, "exp": expires_at, "jti": secrets.token_hex(16)}
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=["HS256"])


def create_mobile_verification_token(user_id: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "userId": user_id,
        "purpose": "mobile_verification",
        "exp": expires_at,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")


def decode_mobile_verification_token(token: str) -> str:
    payload = decode_access_token(token)
    if payload.get("purpose") != "mobile_verification" or not payload.get("userId"):
        raise ValueError("Invalid mobile verification token")
    return str(payload["userId"])

def generate_email_verification_token() -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    token, session_token = read_auth_cookies(request)
    if not token or not session_token:
        raise credentials_exception
    try:
        payload = decode_access_token(token)
        if payload.get("purpose"):
            raise credentials_exception
        user_id: str = payload.get("userId")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    try:
        if not validate_session(user_id, session_token):
            raise credentials_exception
    except HTTPException:
        raise
    except Exception as exc:
        raise credentials_exception from exc
    return user


def require_credits(amount: float):
    def _checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        from app.services.credit_service import check_credits
        check_credits(db, current_user.id, amount)
        return current_user
    return _checker


def enforce_limits(resource_type: str = None):
    """
    Decorator to enforce subscription status and plan limits.
    
    Args:
        resource_type: Type of resource being created (e.g., 'project', 'keyword', 'competitor', 'report')
    
    This decorator checks that the account has access to the selected plan and
    has not exceeded the relevant plan limit.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract db and user from kwargs or args
            db = kwargs.get('db')
            user = kwargs.get('current_user') or kwargs.get('user')
            
            if not db or not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing db or user in endpoint"
                )
            
            # If user is a dict (from deps.get_current_user), convert to User ORM object
            if isinstance(user, dict):
                user_id = user.get("id") or user.get("userId")
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token"
                    )
                db_user = db.query(User).filter(User.id == user_id).first()
                if db_user is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found"
                    )
                user = db_user
            
            # Import here to avoid circular dependency
            from app.services.plan_service import (
                ensure_subscription_active,
                ensure_project_limit,
                ensure_keyword_limit,
                ensure_competitor_limit,
                get_user_plan_limits
            )
            
            # Check subscription status
            ensure_subscription_active(user)
            
            # Check specific resource limits if resource_type is provided
            if resource_type:
                limits = get_user_plan_limits(user)
                
                if resource_type == 'keyword':
                    ensure_keyword_limit(db, user.id)
                elif resource_type == 'competitor':
                    project_id = kwargs.get('project_id')
                    if not project_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="project_id required for competitor limit check"
                        )
                    ensure_competitor_limit(db, user.id, project_id)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
