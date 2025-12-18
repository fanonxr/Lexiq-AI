"""Pydantic models for lead/intake endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LeadCreateRequest(BaseModel):
    """Request model for creating a lead (LexiqAI-native)."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    full_name: str = Field(..., description="Lead full name")
    email: Optional[str] = Field(None, description="Lead email")
    phone: Optional[str] = Field(None, description="Lead phone number")
    matter_type: Optional[str] = Field(None, description="Optional matter type/category")
    summary: Optional[str] = Field(None, description="Optional short intake summary")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Idempotency key")


class LeadResponse(BaseModel):
    """Response model for a lead."""

    lead_id: str = Field(..., description="Lead ID")
    firm_id: Optional[str] = Field(None, description="Firm ID")
    full_name: str = Field(..., description="Lead full name")
    email: Optional[str] = Field(None, description="Lead email")
    phone: Optional[str] = Field(None, description="Lead phone")
    matter_type: Optional[str] = Field(None, description="Matter type")
    summary: Optional[str] = Field(None, description="Intake summary")
    status: str = Field(..., description="Lead status")
    created_at: datetime = Field(..., description="Created at timestamp")


