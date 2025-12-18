"""Pydantic models for firm configuration endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FirmPersonaUpsertRequest(BaseModel):
    """Request model for setting/updating a firm's system prompt/persona."""

    system_prompt: str = Field(..., description="Firm-specific system prompt/persona text")


class FirmPersonaResponse(BaseModel):
    """Response model for firm persona."""

    firm_id: str
    system_prompt: str
    updated_at: datetime


class FirmSettingsResponse(BaseModel):
    """Response model for full firm settings (for Cognitive Orchestrator)."""

    firm_id: str
    name: str
    domain: Optional[str] = None
    default_model: Optional[str] = Field(None, description="Model override (e.g., 'azure/gpt-4o')")
    system_prompt: Optional[str] = Field(None, description="Custom persona/system prompt")
    specialties: Optional[str] = Field(None, description="JSON array of specialties")
    qdrant_collection: Optional[str] = Field(None, description="Qdrant collection name for this firm")
    created_at: datetime
    updated_at: datetime


