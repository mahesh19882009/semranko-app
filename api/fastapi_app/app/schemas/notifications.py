from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class NotificationCreateSchema(BaseModel):
    title: str
    message: str
    type: str
    projectId: Optional[str] = None
    severity: Optional[str] = "info"
    entityType: Optional[str] = None
    entityId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class NotificationItemSchema(BaseModel):
    id: str
    userId: str
    projectId: Optional[str] = None
    type: str
    title: str
    message: str
    status: str
    severity: str
    entityType: Optional[str] = None
    entityId: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    readAt: Optional[datetime] = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class NotificationListDataSchema(BaseModel):
    items: List[NotificationItemSchema]
    pagination: Dict[str, Any]
    unreadCount: int


class NotificationListResponseSchema(BaseModel):
    success: bool
    message: str
    data: NotificationListDataSchema


class NotificationSingleResponseSchema(BaseModel):
    success: bool
    message: str
    data: NotificationItemSchema


class NotificationUnreadCountResponseSchema(BaseModel):
    success: bool
    message: str
    data: dict


class NotificationActionResponseSchema(BaseModel):
    success: bool
    message: str
    data: dict