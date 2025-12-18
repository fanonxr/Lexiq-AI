"""Pydantic models for appointments and scheduling endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AvailabilityRequest(BaseModel):
    """Request model for checking availability within a time window."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    timezone: str = Field(..., description="IANA timezone (e.g., 'America/New_York')")
    window_start: datetime = Field(..., description="Start of search window (ISO8601)")
    window_end: datetime = Field(..., description="End of search window (ISO8601)")
    duration_minutes: int = Field(30, ge=5, le=240, description="Appointment duration in minutes")
    appointment_type: Optional[str] = Field(
        None, description="Optional appointment type (e.g., 'consultation')"
    )


class AvailabilitySlot(BaseModel):
    """A single availability slot."""

    start: datetime = Field(..., description="Slot start (timezone-aware ISO8601)")
    end: datetime = Field(..., description="Slot end (timezone-aware ISO8601)")
    timezone: str = Field(..., description="Timezone for this slot (IANA)")


class AvailabilityResponse(BaseModel):
    """Response model for availability check."""

    firm_id: str = Field(..., description="Firm ID")
    timezone: str = Field(..., description="Timezone used for computation (IANA)")
    duration_minutes: int = Field(..., description="Duration used for slots")
    slots: List[AvailabilitySlot] = Field(default_factory=list, description="Candidate slots")


class AppointmentContact(BaseModel):
    """Contact information for an appointment."""

    full_name: str = Field(..., description="Contact full name")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone number")


class AppointmentCreateRequest(BaseModel):
    """Request model for booking an appointment (LexiqAI-native)."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    timezone: str = Field(..., description="IANA timezone (e.g., 'America/New_York')")
    start: datetime = Field(..., description="Appointment start time (ISO8601)")
    duration_minutes: int = Field(..., ge=5, le=240, description="Duration in minutes")
    title: Optional[str] = Field(None, description="Optional appointment title")
    contact: AppointmentContact = Field(..., description="Contact info for the appointment")
    notes: Optional[str] = Field(None, description="Optional notes")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Idempotency key")


class AppointmentResponse(BaseModel):
    """Response model for a booked appointment."""

    appointment_id: str = Field(..., description="Appointment ID")
    firm_id: Optional[str] = Field(None, description="Firm ID")
    timezone: str = Field(..., description="Timezone")
    start: datetime = Field(..., description="Start time")
    end: datetime = Field(..., description="End time")
    duration_minutes: int = Field(..., description="Duration in minutes")
    status: str = Field(..., description="Appointment status (booked, canceled, etc.)")
    title: Optional[str] = Field(None, description="Title")
    contact: AppointmentContact = Field(..., description="Contact info")
    notes: Optional[str] = Field(None, description="Notes")
    created_at: datetime = Field(..., description="Created at timestamp")


