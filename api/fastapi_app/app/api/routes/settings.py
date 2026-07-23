from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.services.settings_service import (
    get_my_settings_service,
    update_notification_settings_service,
    update_password_service,
    update_profile_service,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/me")
def get_my_settings(user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    data = get_my_settings_service(db, user["userId"])
    return ok("Settings fetched successfully", data)


@router.put("/profile")
def update_profile(payload: dict = Body(...), user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    data = update_profile_service(db, user["userId"], payload)
    return ok("Profile updated successfully", data)


@router.put("/notifications")
def update_notifications(payload: dict = Body(...), user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    data = update_notification_settings_service(db, user["userId"], payload)
    return ok("Notification settings updated successfully", data)


@router.put("/password")
def update_password(payload: dict = Body(...), user: dict = Depends(get_current_user), db: Session = Depends(db_session)) -> dict:
    update_password_service(db, user["userId"], payload)
    return ok("Password updated successfully", None)
