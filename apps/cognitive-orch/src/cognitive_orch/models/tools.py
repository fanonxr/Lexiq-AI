"""Pydantic models for LLM tool execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Normalized representation of a single tool call from the LLM."""

    tool_name: str = Field(..., description="Tool name (must be allowlisted)")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments as JSON object")
    tool_call_id: Optional[str] = Field(
        default=None, description="Provider tool call id (for correlating tool results)"
    )


class ToolError(BaseModel):
    """Structured tool error object."""

    code: str = Field(..., description="Stable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Optional debugging details")


class ToolResult(BaseModel):
    """Normalized representation of a tool execution result."""

    tool_name: str = Field(..., description="Tool name")
    tool_call_id: Optional[str] = Field(None, description="Tool call id (if provided by the LLM)")
    success: bool = Field(..., description="Whether the tool execution succeeded")
    data: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific output payload")
    error: Optional[ToolError] = Field(None, description="Tool error when success=false")


class CheckAvailabilityArgs(BaseModel):
    """Arguments for `check_availability` tool."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    timezone: str = Field(..., description="IANA timezone (e.g., 'America/New_York')")
    window_start: datetime = Field(..., description="Start of search window (ISO8601)")
    window_end: datetime = Field(..., description="End of search window (ISO8601)")
    duration_minutes: int = Field(30, ge=5, le=240, description="Appointment duration in minutes")
    appointment_type: Optional[str] = Field(
        None, description="Optional appointment type (e.g., 'consultation')"
    )


class AvailabilitySlot(BaseModel):
    """Availability slot returned by Core API."""

    start: datetime
    end: datetime
    timezone: str


class CheckAvailabilityResult(BaseModel):
    """Tool result payload for `check_availability`."""

    firm_id: str
    timezone: str
    duration_minutes: int
    slots: List[AvailabilitySlot] = Field(default_factory=list)


class AppointmentContact(BaseModel):
    """Contact info for booking tools."""

    full_name: str = Field(..., description="Contact full name")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")


class BookAppointmentArgs(BaseModel):
    """Arguments for `book_appointment` tool."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    timezone: str = Field(..., description="IANA timezone (e.g., 'America/New_York')")
    start: datetime = Field(..., description="Appointment start time (ISO8601)")
    duration_minutes: int = Field(..., ge=5, le=240, description="Duration in minutes")
    title: Optional[str] = Field(None, description="Optional appointment title")
    contact: AppointmentContact = Field(..., description="Contact info")
    notes: Optional[str] = Field(None, description="Optional notes")
    confirmed: bool = Field(..., description="Must be true only after explicit user confirmation")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Idempotency key")


class BookAppointmentResult(BaseModel):
    """Tool result payload for `book_appointment`."""

    appointment_id: str
    firm_id: Optional[str] = None
    timezone: str
    start: datetime
    end: datetime
    duration_minutes: int
    status: str
    title: Optional[str] = None
    contact: AppointmentContact
    notes: Optional[str] = None
    created_at: datetime


class CreateLeadArgs(BaseModel):
    """Arguments for `create_lead` tool."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    full_name: str = Field(..., description="Lead full name")
    email: Optional[str] = Field(None, description="Lead email")
    phone: Optional[str] = Field(None, description="Lead phone")
    matter_type: Optional[str] = Field(None, description="Optional matter type/category")
    summary: Optional[str] = Field(None, description="Optional intake summary")
    confirmed: bool = Field(..., description="Must be true only after explicit user confirmation")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Idempotency key")


class CreateLeadResult(BaseModel):
    """Tool result payload for `create_lead`."""

    lead_id: str
    firm_id: Optional[str] = None
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    matter_type: Optional[str] = None
    summary: Optional[str] = None
    status: str
    created_at: datetime


class SendNotificationArgs(BaseModel):
    """Arguments for `send_notification` tool."""

    firm_id: str = Field(..., description="Firm ID (multi-tenant scope)")
    channel: str = Field(..., description="Notification channel: email|sms")
    to: str = Field(..., description="Destination address/number")
    subject: Optional[str] = Field(None, description="Subject (email only)")
    message: str = Field(..., description="Message body")
    confirmed: bool = Field(..., description="Must be true only after explicit user confirmation")
    idempotency_key: str = Field(..., min_length=8, max_length=128, description="Idempotency key")


class SendNotificationResult(BaseModel):
    """Tool result payload for `send_notification`."""

    notification_id: str
    firm_id: Optional[str] = None
    channel: str
    to: str
    subject: Optional[str] = None
    message: str
    status: str
    created_at: datetime


# ===== CLIENT INFORMATION MANAGEMENT TOOLS =====


class UpdateClientInfoArgs(BaseModel):
    """Arguments for `update_client_info` tool."""

    client_id: str = Field(..., description="Client UUID (provided by system)")
    first_name: Optional[str] = Field(None, description="Client's first name")
    last_name: Optional[str] = Field(None, description="Client's last name")
    email: Optional[str] = Field(None, description="Client's email address")
    external_crm_id: Optional[str] = Field(None, description="External CRM identifier")


class UpdateClientInfoResult(BaseModel):
    """Tool result payload for `update_client_info`."""

    client_id: str
    updated_fields: List[str] = Field(default_factory=list, description="List of fields that were updated")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    external_crm_id: Optional[str] = None
