from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.db.models import User
from app.utils.serializers import model_to_dict


def _public_user(user: User) -> dict:
    return model_to_dict(user, exclude={"passwordHash"})


def get_my_settings_service(db: Session, user_id: str) -> dict:
    if not user_id:
        raise ApiError(401, "Unauthorized")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")

    return _public_user(user)


def update_profile_service(db: Session, user_id: str, payload: dict) -> dict:
    if not user_id:
        raise ApiError(401, "Unauthorized")

    if payload.get("email") is not None:
        raise ApiError(400, "Email cannot be changed")

    name = payload.get("name")
    if not name or not name.strip():
        raise ApiError(400, "Name is required")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")

    user.name = name.strip()
    db.commit()
    db.refresh(user)
    return _public_user(user)


def update_notification_settings_service(db: Session, user_id: str, payload: dict) -> dict:
    if not user_id:
        raise ApiError(401, "Unauthorized")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")

    user.dailyKeywordMovement = bool(payload.get("dailyKeywordMovement"))
    user.weeklyAuditSummary = bool(payload.get("weeklyAuditSummary"))
    user.competitorAlerts = bool(payload.get("competitorAlerts"))

    db.commit()
    db.refresh(user)
    return _public_user(user)


def update_password_service(db: Session, user_id: str, payload: dict) -> bool:
    if not user_id:
        raise ApiError(401, "Unauthorized")

    current_password = payload.get("currentPassword")
    new_password = payload.get("newPassword")
    confirm_password = payload.get("confirmPassword")

    if not current_password or not new_password or not confirm_password:
        raise ApiError(400, "All password fields are required")

    if len(new_password) < 8:
        raise ApiError(400, "New password must be at least 8 characters")

    if new_password != confirm_password:
        raise ApiError(400, "New password and confirm password do not match")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise ApiError(404, "User not found")

    if not verify_password(current_password, user.passwordHash):
        raise ApiError(401, "Current password is incorrect")

    if verify_password(new_password, user.passwordHash):
        raise ApiError(400, "New password must be different from current password")

    user.passwordHash = hash_password(new_password)
    db.commit()
    return True
