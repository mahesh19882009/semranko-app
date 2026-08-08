from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.db.models import User


def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> dict:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        raise ApiError(401, "Unauthorized")

    try:
        payload = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(401, "Invalid token") from exc

    user_id = payload.get("userId")
    if not user_id:
        raise ApiError(401, "Invalid token")

    user = db.scalar(select(User).where(User.id == user_id))
    if user:
        payload["selectedPlan"] = user.selectedPlan
        payload["subscriptionStatus"] = user.subscriptionStatus
        payload["trialEndsAt"] = user.trialEndsAt.isoformat() if user.trialEndsAt else None
        payload["creditBalance"] = user.creditBalance

    payload["id"] = user_id
    return payload


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


def require_team_action(db: Session = Depends(db_session), current_user: dict = Depends(get_current_user)):
    from app.services.team_service import get_team_owner_id
    owner_id = get_team_owner_id(db, current_user["id"])
    return {"db": db, "owner_id": owner_id, "user_id": current_user["id"]}


def verify_user_access_privileges(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
    allow_free_trial_bulk: bool = False,
):
    """
    Global access dependency gatekeeper to verify user subscription and credit balance.
    
    Args:
        allow_free_trial_bulk: If True, allows free_trial users to access bulk operations (default: False)
    
    Raises:
        HTTPException 402: If user is expired or has insufficient credits
        HTTPException 403: If free_trial user attempts bulk/AIO operations (when not allowed)
    """
    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is expired or has insufficient credits
    if user.subscriptionStatus == "expired" or (user.creditBalance or 0) <= 0:
        raise HTTPException(
            status_code=402,
            detail="Payment Required: Your subscription has expired or you have insufficient credits. Please upgrade your plan or purchase credits."
        )
    
    return user


def verify_user_access_privileges_allow_bulk(
    db: Session = Depends(db_session),
    current_user: dict = Depends(get_current_user),
):
    """Wrapper that allows free_trial users to access bulk operations."""
    return verify_user_access_privileges(db, current_user, allow_free_trial_bulk=True)

