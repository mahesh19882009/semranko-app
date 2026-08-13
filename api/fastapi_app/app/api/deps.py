from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.core.session import validate_session
from app.db.session import get_db
from app.db.models import User
from app.core.auth_cookies import read_auth_cookies


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    token, session_token = read_auth_cookies(request)
    if not token:
        raise ApiError(401, "Unauthorized")

    try:
        payload = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(401, "Invalid token") from exc

    if payload.get("purpose"):
        raise ApiError(401, "Invalid token")
    user_id = payload.get("userId")
    if not user_id:
        raise ApiError(401, "Invalid token")

    if not session_token:
        raise ApiError(401, "Session expired or invalid")

    try:
        if not validate_session(user_id, session_token):
            raise ApiError(401, "Session expired or invalid")
    except Exception:
        raise ApiError(401, "Session expired or invalid")

    user = db.scalar(select(User).where(User.id == user_id))
    if user:
        payload["selectedPlan"] = user.selectedPlan
        is_free = (user.selectedPlan or "free_trial").strip().lower() == "free_trial"
        payload["subscriptionStatus"] = "free" if is_free else user.subscriptionStatus
        payload["trialEndsAt"] = None if is_free else (user.trialEndsAt.isoformat() if user.trialEndsAt else None)
        payload["creditBalance"] = user.creditBalance
        payload["automaticCreditBalance"] = user.automaticCreditBalance

    payload["id"] = user_id
    return payload


def db_session(db: Session = Depends(get_db)) -> Session:
    return db


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
    
    # Free remains accessible even if a historical row has an expired status or
    # zero credits. Paid plans retain the existing expiry/credit gate.
    is_free = (user.selectedPlan or "free_trial").strip().lower() == "free_trial"
    if not is_free and (user.subscriptionStatus == "expired" or (user.creditBalance or 0) <= 0):
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
