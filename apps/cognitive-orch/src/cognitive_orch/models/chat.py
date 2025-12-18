"""Chat API models for the Cognitive Orchestrator."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for orchestrator chat endpoint."""

    message: str = Field(..., description="User message")
    user_id: str = Field(..., description="User ID")
    firm_id: Optional[str] = Field(None, description="Optional firm ID (multi-tenant)")
    conversation_id: Optional[str] = Field(None, description="Optional conversation id (UUID)")
    tools_enabled: bool = Field(True, description="Enable tool calling")
    model: Optional[str] = Field(None, description="Optional model override (LiteLLM format)")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Sampling temperature")


class ChatResponse(BaseModel):
    """Response model for orchestrator chat endpoint."""

    conversation_id: str
    response: str
    tool_results: list[Dict[str, Any]] = Field(default_factory=list)
    iterations: int = Field(1, description="Tool loop iterations (1 means no tool calls)")


