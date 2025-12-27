"""Pydantic models for firm configuration endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


class FirmPhoneNumberRequest(BaseModel):
    """Request model for provisioning a phone number for a firm."""

    area_code: Optional[str] = Field(
        None,
        description="Preferred area code (e.g., '415', '212'). Optional - system will search for available numbers.",
        min_length=3,
        max_length=3,
    )

    @field_validator("area_code")
    @classmethod
    def validate_area_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate area code format."""
        if v and not v.isdigit():
            raise ValueError("Area code must be numeric")
        return v


class FirmPhoneNumberResponse(BaseModel):
    """Response model for firm phone number."""

    firm_id: str
    phone_number: str  # E.164 format
    twilio_phone_number_sid: str
    twilio_subaccount_sid: str  # Subaccount SID
    formatted_phone_number: str  # Human-readable format (e.g., (555) 123-4567)
    area_code: Optional[str] = None  # Area code of the number

    @staticmethod
    def _format_phone_number(phone: str) -> str:
        """Format E.164 phone number for display."""
        if phone.startswith("+1") and len(phone) == 12:
            area = phone[2:5]
            prefix = phone[5:8]
            number = phone[8:]
            return f"({area}) {prefix}-{number}"
        return phone

    @classmethod
    def from_phone_number(
        cls,
        firm_id: str,
        phone_number: str,
        twilio_phone_number_sid: str,
        twilio_subaccount_sid: str,
    ) -> "FirmPhoneNumberResponse":
        """Create response from phone number components."""
        area_code = phone_number[2:5] if phone_number.startswith("+1") and len(phone_number) == 12 else None
        formatted = cls._format_phone_number(phone_number)

        return cls(
            firm_id=firm_id,
            phone_number=phone_number,
            twilio_phone_number_sid=twilio_phone_number_sid,
            twilio_subaccount_sid=twilio_subaccount_sid,
            formatted_phone_number=formatted,
            area_code=area_code,
        )


