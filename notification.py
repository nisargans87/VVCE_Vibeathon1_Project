"""Pydantic schemas for notification endpoints."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NotificationTypeEnum(str, Enum):
    """Notification category."""

    transaction = "transaction"
    security = "security"
    system = "system"
    fraud_alert = "fraud_alert"


class NotificationChannelEnum(str, Enum):
    """Notification delivery channel."""

    email = "email"
    in_app = "in_app"
    both = "both"


class NotificationFilter(BaseModel):
    """Schema for filtering notifications.

    Validates: Requirements 9.3
    """

    model_config = {"strict": False}

    type: NotificationTypeEnum | None = None
    is_read: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class NotificationResponse(BaseModel):
    """Schema for a single notification in responses.

    Validates: Requirements 9.3, 15.3
    """

    model_config = {"strict": False, "from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationTypeEnum
    channel: NotificationChannelEnum
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)
    metadata: dict | None = None
    is_read: bool
    email_sent: bool
    email_sent_at: datetime | None = None
    created_at: datetime


class NotificationPayload(BaseModel):
    """Schema for creating a new notification.

    Validates: Requirements 9.1, 9.2, 15.3
    """

    model_config = {"strict": False}

    type: NotificationTypeEnum
    channel: NotificationChannelEnum = NotificationChannelEnum.both
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)
    metadata: dict | None = None
