"""Pydantic models for call endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CallResponse(BaseModel):
    """Response model for a call."""

    id: str
    user_id: str
    conversation_id: Optional[str] = None
    phone_number: str
    direction: str = Field(..., description="inbound or outbound")
    status: str = Field(
        ...,
        description="Call status: initiated, ringing, in-progress, completed, failed, missed",
    )
    duration_seconds: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    twilio_call_sid: Optional[str] = None
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CallCreateRequest(BaseModel):
    """Request model for creating a call."""

    user_id: str
    conversation_id: Optional[str] = None
    phone_number: str
    direction: str = Field(..., description="inbound or outbound")
    status: str = Field(default="initiated", description="Call status")
    twilio_call_sid: Optional[str] = None


class CallUpdateRequest(BaseModel):
    """Request model for updating a call."""

    status: Optional[str] = None
    duration_seconds: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class CallListResponse(BaseModel):
    """Response model for listing calls."""

    calls: List[CallResponse]
    total: int

