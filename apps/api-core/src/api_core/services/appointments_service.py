"""Appointments and scheduling service.

NOTE: This initial implementation returns *candidate* slots using simple business-hour rules.
It does not yet account for:
- Staff calendars / external calendars
- Existing bookings
- Firm-specific scheduling rules

Those can be layered in later with persistent appointment models and integrations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from api_core.database.models import Appointment
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.appointments import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AvailabilityRequest,
    AvailabilityResponse,
    AvailabilitySlot,
)
from api_core.repositories.appointments_repository import AppointmentsRepository


@dataclass(frozen=True)
class BusinessHours:
    """Simple business hours window for a day."""

    start: time
    end: time


class AppointmentsService:
    """Service for LexiqAI-native scheduling operations."""

    def __init__(self, session=None) -> None:
        # Session is optional: availability doesn't require DB; booking does.
        self._session = session
        self._repo = AppointmentsRepository(session) if session is not None else None
        # Default hours for MVP: Mon–Fri, 9am–5pm local time
        self._business_hours = BusinessHours(start=time(9, 0), end=time(17, 0))

    def get_availability(self, request: AvailabilityRequest) -> AvailabilityResponse:
        """Compute candidate slots inside the requested window.

        This is intentionally deterministic and conservative for MVP.
        """
        tz = ZoneInfo(request.timezone)

        window_start = request.window_start
        window_end = request.window_end

        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz)
        else:
            window_start = window_start.astimezone(tz)

        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=tz)
        else:
            window_end = window_end.astimezone(tz)

        if window_end <= window_start:
            return AvailabilityResponse(
                firm_id=request.firm_id,
                timezone=request.timezone,
                duration_minutes=request.duration_minutes,
                slots=[],
            )

        duration = timedelta(minutes=request.duration_minutes)
        step = duration  # simple step = duration (can evolve later)

        # Cap results to avoid huge payloads for large windows
        max_slots = 50
        slots: List[AvailabilitySlot] = []

        cursor = window_start
        while cursor + duration <= window_end and len(slots) < max_slots:
            # Weekday only (Mon=0..Sun=6)
            if cursor.weekday() < 5:
                day_start = datetime.combine(cursor.date(), self._business_hours.start, tzinfo=tz)
                day_end = datetime.combine(cursor.date(), self._business_hours.end, tzinfo=tz)

                candidate_start = cursor
                candidate_end = candidate_start + duration

                if candidate_start >= day_start and candidate_end <= day_end:
                    slots.append(
                        AvailabilitySlot(
                            start=candidate_start,
                            end=candidate_end,
                            timezone=request.timezone,
                        )
                    )

            cursor = cursor + step

        return AvailabilityResponse(
            firm_id=request.firm_id,
            timezone=request.timezone,
            duration_minutes=request.duration_minutes,
            slots=slots,
        )

    async def book_appointment(self, request: AppointmentCreateRequest) -> AppointmentResponse:
        """Book an appointment (idempotent).

        Requires DB session.
        """
        if self._repo is None or self._session is None:
            raise RuntimeError("AppointmentsService requires a database session for booking")

        # Idempotency check
        existing = await self._repo.get_by_idempotency_key(request.idempotency_key)
        if existing:
            return AppointmentResponse(
                appointment_id=existing.id,
                firm_id=existing.firm_id,
                timezone=existing.timezone,
                start=existing.start_at,
                end=existing.end_at,
                duration_minutes=existing.duration_minutes,
                status=existing.status,
                title=existing.title,
                contact={
                    "full_name": existing.contact_full_name,
                    "email": existing.contact_email,
                    "phone": existing.contact_phone,
                },  # pydantic will coerce
                notes=existing.notes,
                created_at=existing.created_at,
            )

        tz = ZoneInfo(request.timezone)

        start = request.start
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        else:
            start = start.astimezone(tz)

        duration = timedelta(minutes=request.duration_minutes)
        end = start + duration

        # Validate weekday + business hours
        if start.weekday() >= 5:
            raise ValidationError("Appointments can only be booked on weekdays (Mon–Fri).")

        day_start = datetime.combine(start.date(), self._business_hours.start, tzinfo=tz)
        day_end = datetime.combine(start.date(), self._business_hours.end, tzinfo=tz)
        if start < day_start or end > day_end:
            raise ValidationError("Requested time is outside business hours (9am–5pm).")

        created = await self._repo.create(
            firm_id=request.firm_id,
            timezone=request.timezone,
            start_at=start,
            end_at=end,
            duration_minutes=request.duration_minutes,
            title=request.title,
            notes=request.notes,
            status="booked",
            contact_full_name=request.contact.full_name,
            contact_email=request.contact.email,
            contact_phone=request.contact.phone,
            idempotency_key=request.idempotency_key,
        )

        return AppointmentResponse(
            appointment_id=created.id,
            firm_id=created.firm_id,
            timezone=created.timezone,
            start=created.start_at,
            end=created.end_at,
            duration_minutes=created.duration_minutes,
            status=created.status,
            title=created.title,
            contact={
                "full_name": created.contact_full_name,
                "email": created.contact_email,
                "phone": created.contact_phone,
            },
            notes=created.notes,
            created_at=created.created_at,
        )

    async def get_user_appointments(
        self,
        user_id: str,
        firm_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        clients_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Appointment]:
        """
        Get appointments for a user.
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            clients_only: If True, only return appointments created through LexiqAI (source_calendar_id IS NULL)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Appointment models
        """
        if self._repo is None:
            raise RuntimeError("AppointmentsService requires a database session for user operations")
        
        return await self._repo.get_by_user_id(
            user_id=user_id,
            firm_id=firm_id,
            start_date=start_date,
            end_date=end_date,
            clients_only=clients_only,
            skip=skip,
            limit=limit,
        )

    async def update_appointment(
        self,
        appointment_id: str,
        user_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        status: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
    ) -> Appointment:
        """
        Update an appointment.
        
        Args:
            appointment_id: Appointment ID
            user_id: User ID (for authorization check)
            title: Optional title to update
            notes: Optional notes to update
            status: Optional status to update
            start_at: Optional start time to update
            end_at: Optional end time to update
            
        Returns:
            Updated Appointment model
        """
        if self._repo is None:
            raise RuntimeError("AppointmentsService requires a database session for update operations")
        
        appointment = await self._repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError(resource="Appointment", resource_id=appointment_id)
        
        # Check authorization - user must have created it or belong to the firm
        if appointment.created_by_user_id != user_id:
            # Check if user belongs to the firm
            if not appointment.firm_id:
                raise AuthorizationError(f"User {user_id} does not have access to appointment {appointment_id}")
            # TODO: Add firm membership check if needed
        
        # Update fields
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if notes is not None:
            update_data["notes"] = notes
        if status is not None:
            update_data["status"] = status
        if start_at is not None:
            update_data["start_at"] = start_at
        if end_at is not None:
            update_data["end_at"] = end_at
        
        if not update_data:
            return appointment
        
        return await self._repo.update(appointment_id, **update_data)

    async def cancel_appointment(
        self,
        appointment_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> Appointment:
        """
        Cancel an appointment.
        
        Args:
            appointment_id: Appointment ID
            user_id: User ID (for authorization check)
            reason: Optional cancellation reason
            
        Returns:
            Cancelled Appointment model
        """
        return await self.update_appointment(
            appointment_id=appointment_id,
            user_id=user_id,
            status="cancelled",
            notes=reason if reason else None,
        )


_appointments_service: AppointmentsService | None = None


def get_appointments_service() -> AppointmentsService:
    """Get a process-global AppointmentsService instance."""
    global _appointments_service
    if _appointments_service is None:
        _appointments_service = AppointmentsService()
    return _appointments_service


def get_appointments_service_for_session(session) -> AppointmentsService:
    """Create an AppointmentsService bound to a DB session (for booking)."""
    return AppointmentsService(session=session)


