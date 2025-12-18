"""Pydantic models for notifications endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


NotificationChannel = Literal["email", "sms"]


class NotificationCreateRequest(BaseModel):
    """Request model for creating a notification (LexiqAI-native outbox)."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    channel: NotificationChannel = Field(..., description="Notification channel: email|sms")
    to: str = Field(..., description="Destination address/number")
    subject: Optional[str] = Field(None, description="Email subject (email only)")
    message: str = Field(..., description="Message body")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Idempotency key")


class NotificationResponse(BaseModel):
    """Response model for a notification record."""

    notification_id: str = Field(..., description="Notification ID")
    firm_id: Optional[str] = Field(None, description="Firm ID")
    channel: NotificationChannel = Field(..., description="Notification channel")
    to: str = Field(..., description="Destination")
    subject: Optional[str] = Field(None, description="Subject")
    message: str = Field(..., description="Message")
    status: str = Field(..., description="Status (queued/sent/failed)")
    created_at: datetime = Field(..., description="Created at timestamp")


