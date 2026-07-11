from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.errors import ApiError
from app.schemas.notifications import (
    NotificationActionResponseSchema,
    NotificationListResponseSchema,
    NotificationSingleResponseSchema,
    NotificationUnreadCountResponseSchema,
    NotificationCreateSchema,
)
from app.services.notification_service import (
    delete_notification,
    get_notifications,
    get_unread_notification_count,
    mark_all_notifications_read,
    mark_notification_read,
    create_notification,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponseSchema)
def list_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default="ALL"),
    projectId: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    data = get_notifications(
        db,
        user_id=user["userId"],
        page=page,
        limit=limit,
        status=status,
        project_id=projectId,
    )
    return {
        "success": True,
        "message": "Notifications fetched successfully",
        "data": data,
    }


@router.get("/unread-count", response_model=NotificationUnreadCountResponseSchema)
def unread_count(
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    count = get_unread_notification_count(db, user_id=user["userId"])
    return {
        "success": True,
        "message": "Unread count fetched successfully",
        "data": {"unreadCount": count},
    }


@router.patch("/{notification_id}/read", response_model=NotificationSingleResponseSchema)
def read_notification(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    notification = mark_notification_read(db, user_id=user["userId"], notification_id=notification_id)
    if not notification:
        raise ApiError(404, "Notification not found")

    return {
        "success": True,
        "message": "Notification marked as read successfully",
        "data": notification,
    }


@router.patch("/read-all", response_model=NotificationActionResponseSchema)
def read_all_notifications(
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    data = mark_all_notifications_read(db, user_id=user["userId"])
    return {
        "success": True,
        "message": "All notifications marked as read successfully",
        "data": data,
    }

@router.post("", response_model=NotificationSingleResponseSchema)
def create_manual_notification(
    payload: NotificationCreateSchema,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    notification = create_notification(
        db,
        user_id=user["userId"],
        title=payload.title,
        message=payload.message,
        type=payload.type,
        project_id=payload.projectId,
        severity=payload.severity,
        entity_type=payload.entityType,
        entity_id=payload.entityId,
        metadata=payload.metadata,
    )

    return {
        "success": True,
        "message": "Notification created successfully",
        "data": notification,
    }

@router.delete("/{notification_id}", response_model=NotificationActionResponseSchema)
def remove_notification(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    deleted = delete_notification(db, user_id=user["userId"], notification_id=notification_id)
    if not deleted:
        raise ApiError(404, "Notification not found")

    return {
        "success": True,
        "message": "Notification deleted successfully",
        "data": {},
    }