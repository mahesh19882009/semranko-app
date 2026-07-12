from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Notification
from app.utils.serializers import model_to_dict


def create_notification(
    db: Session,
    *,
    user_id: str,
    title: str,
    message: str,
    type: str,
    project_id: Optional[str] = None,
    severity: str = "info",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    notification = Notification(
        userId=user_id,
        title=title,
        message=message,
        type=type,
        projectId=project_id,
        severity=severity,
        entityType=entity_type,
        entityId=entity_id,
        payload=metadata,
        status="UNREAD",
    )
    db.add(notification)
    db.flush()
    db.refresh(notification)
    return model_to_dict(notification)


def get_notifications(
    db: Session,
    *,
    user_id: str,
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
) -> dict:
    query = select(Notification).where(Notification.userId == user_id)

    if status and status.upper() != "ALL":
        query = query.where(Notification.status == status.upper())

    if project_id:
        query = query.where(Notification.projectId == project_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    items = db.scalars(
        query.order_by(Notification.createdAt.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    unread_count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.userId == user_id,
            Notification.status == "UNREAD",
        )
    ) or 0

    return {
        "items": [model_to_dict(item) for item in items],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": (total + limit - 1) // limit if total else 0,
        },
        "unreadCount": unread_count,
    }


def get_unread_notification_count(db: Session, *, user_id: str) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(
            Notification.userId == user_id,
            Notification.status == "UNREAD",
        )
    ) or 0


def mark_notification_read(db: Session, *, user_id: str, notification_id: str) -> Optional[dict]:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.userId == user_id,
        )
    )

    if not notification:
        return None

    if notification.status != "READ":
        notification.status = "READ"
        notification.readAt = datetime.utcnow()
        notification.updatedAt = datetime.utcnow()
        db.commit()
        db.refresh(notification)

    return model_to_dict(notification)


def mark_all_notifications_read(db: Session, *, user_id: str) -> dict:
    notifications = db.scalars(
        select(Notification).where(
            Notification.userId == user_id,
            Notification.status == "UNREAD",
        )
    ).all()

    now = datetime.utcnow()
    updated_count = 0

    for notification in notifications:
        notification.status = "READ"
        notification.readAt = now
        notification.updatedAt = now
        updated_count += 1

    db.commit()

    return {"updatedCount": updated_count}


def delete_notification(db: Session, *, user_id: str, notification_id: str) -> bool:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.userId == user_id,
        )
    )

    if not notification:
        return False

    db.delete(notification)
    db.commit()
    return True