import secrets
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import ApiKey, User
from datetime import datetime, timedelta


def generate_api_key() -> str:
    """
    Generate a secure random API key
    """
    return f"rc_{secrets.token_urlsafe(32)}"


def create_api_key(db: Session, user_id: str, name: str, expires_in_days: Optional[int] = None) -> ApiKey:
    """
    Create a new API key for a user
    """
    key = generate_api_key()
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    api_key = ApiKey(
        userId=user_id,
        key=key,
        name=name,
        isActive=True,
        expiresAt=expires_at
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return api_key


def get_user_api_keys(db: Session, user_id: str) -> List[ApiKey]:
    """
    Get all API keys for a user
    """
    return db.execute(
        select(ApiKey)
        .where(ApiKey.userId == user_id)
        .order_by(ApiKey.createdAt.desc())
    ).scalars().all()


def get_api_key(db: Session, key: str) -> Optional[ApiKey]:
    """
    Get an API key by its value
    """
    return db.execute(
        select(ApiKey)
        .where(ApiKey.key == key)
        .where(ApiKey.isActive == True)
    ).scalar_one_or_none()


def deactivate_api_key(db: Session, api_key_id: str, user_id: str) -> bool:
    """
    Deactivate an API key
    """
    api_key = db.execute(
        select(ApiKey)
        .where(ApiKey.id == api_key_id)
        .where(ApiKey.userId == user_id)
    ).scalar_one_or_none()
    
    if api_key:
        api_key.isActive = False
        db.commit()
        return True
    
    return False


def delete_api_key(db: Session, api_key_id: str, user_id: str) -> bool:
    """
    Delete an API key
    """
    api_key = db.execute(
        select(ApiKey)
        .where(ApiKey.id == api_key_id)
        .where(ApiKey.userId == user_id)
    ).scalar_one_or_none()
    
    if api_key:
        db.delete(api_key)
        db.commit()
        return True
    
    return False


def update_api_key_last_used(db: Session, key: str) -> None:
    """
    Update the last used timestamp for an API key
    """
    api_key = get_api_key(db, key)
    if api_key:
        api_key.lastUsed = datetime.utcnow()
        db.commit()


def validate_api_key(db: Session, key: str) -> Optional[User]:
    """
    Validate an API key and return the associated user
    """
    api_key = get_api_key(db, key)
    
    if not api_key:
        return None
    
    # Check if expired
    if api_key.expiresAt and api_key.expiresAt < datetime.utcnow():
        return None
    
    # Update last used
    update_api_key_last_used(db, key)
    
    # Get user
    user = db.execute(
        select(User)
        .where(User.id == api_key.userId)
    ).scalar_one_or_none()
    
    return user
