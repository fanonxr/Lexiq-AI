"""API models for conversation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationStateResponse(BaseModel):
    """Response model for conversation state."""

    conversation_id: str
    user_id: str
    firm_id: Optional[str] = None
    call_id: Optional[str] = None
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation messages"
    )
    total_tokens: int = Field(default=0, description="Total tokens used")
    model_used: Optional[str] = Field(None, description="Model used in conversation")
    started_at: datetime
    updated_at: datetime


class ClearConversationResponse(BaseModel):
    """Response model for clearing a conversation."""

    success: bool
    message: str
    conversation_id: str

