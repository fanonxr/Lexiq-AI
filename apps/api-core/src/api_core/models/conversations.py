"""Pydantic models for conversation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationMessageResponse(BaseModel):
    """Response model for a conversation message."""

    id: str
    conversation_id: str
    role: str = Field(..., description="Message role: user, assistant, system, or tool")
    content: str
    tool_calls: Optional[str] = Field(None, description="JSON array of tool calls")
    tool_call_id: Optional[str] = None
    tokens: Optional[int] = None
    model: Optional[str] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Response model for a conversation."""

    id: str
    user_id: str
    firm_id: Optional[str] = None
    call_id: Optional[str] = None
    status: str
    model_used: Optional[str] = None
    total_tokens: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageResponse] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    """Response model for listing conversations."""

    conversations: List[ConversationResponse]
    total: int

