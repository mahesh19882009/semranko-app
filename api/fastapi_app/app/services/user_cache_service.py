from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import UserCacheUnlock


def check_user_cache_unlock(db: Session, owner_id: str, target_string: str) -> bool:
    """
    Check if the user has unlocked this cache entry in the last 30 days.
    Returns True if user cache hit (already paid), False if miss.
    """
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    unlock = db.scalar(
        select(UserCacheUnlock).where(
            UserCacheUnlock.ownerId == owner_id,
            UserCacheUnlock.targetString == target_string,
            UserCacheUnlock.unlockedAt >= thirty_days_ago
        )
    )
    
    return unlock is not None


def create_user_cache_unlock(db: Session, owner_id: str, target_string: str) -> UserCacheUnlock:
    """
    Create a new cache unlock record for the user.
    This marks that the user has paid for this data.
    """
    unlock = UserCacheUnlock(
        ownerId=owner_id,
        targetString=target_string,
        unlockedAt=datetime.utcnow()
    )
    db.add(unlock)
    db.flush()
    db.commit()
    return unlock
