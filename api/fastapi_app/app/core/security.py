from datetime import datetime, timedelta, timezone
from typing import Optional
from functools import wraps

import bcrypt
import jwt
import secrets
from hashlib import sha256
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import User


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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("userId")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def enforce_limits(resource_type: str = None):
    """
    Decorator to enforce subscription status and plan limits.
    
    Args:
        resource_type: Type of resource being created (e.g., 'project', 'keyword', 'competitor', 'report')
    
    This decorator checks:
    1. Subscription is active or in trial
    2. Trial has not expired
    3. User has not exceeded plan limits for the resource type
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract db and user from kwargs or args
            db = kwargs.get('db')
            user = kwargs.get('current_user') or kwargs.get('user')
            
            if not db or not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing db or user in endpoint"
                )
            
            # Import here to avoid circular dependency
            from app.services.plan_service import (
                ensure_subscription_active,
                ensure_project_limit,
                ensure_keyword_limit,
                ensure_competitor_limit,
                ensure_report_limit,
                get_user_plan_limits
            )
            
            # Check subscription status
            ensure_subscription_active(user)
            
            # Check specific resource limits if resource_type is provided
            if resource_type:
                limits = get_user_plan_limits(user)
                
                if resource_type == 'project':
                    ensure_project_limit(db, user.id)
                elif resource_type == 'keyword':
                    ensure_keyword_limit(db, user.id)
                elif resource_type == 'competitor':
                    project_id = kwargs.get('project_id')
                    if not project_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="project_id required for competitor limit check"
                        )
                    ensure_competitor_limit(db, user.id, project_id)
                elif resource_type == 'report':
                    ensure_report_limit(db, user.id)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator