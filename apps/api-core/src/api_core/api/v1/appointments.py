"""Appointments endpoints (LexiqAI-native scheduling).

NOTE: For Phase 5 tool execution, these endpoints are primarily used by the Cognitive Orchestrator
as internal service calls.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from api_core.auth.internal_service import InternalAuthDep
from api_core.database.session import get_session_context
from api_core.models.appointments import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AvailabilityRequest,
    AvailabilityResponse,
)
from api_core.services.appointments_service import get_appointments_service, get_appointments_service_for_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post(
    "/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Check appointment availability (Internal)",
    description=(
        "Return candidate appointment slots within a time window. "
        "This endpoint is intended for internal service calls (e.g., Cognitive Orchestrator tools)."
    ),
    dependencies=[InternalAuthDep],
    include_in_schema=False,
)
async def check_availability(request: AvailabilityRequest) -> AvailabilityResponse:
    """Return candidate slots in the requested window.

    This MVP implementation applies simple business-hour rules (Mon–Fri, 9–5 local time).
    """
    service = get_appointments_service()
    try:
        return service.get_availability(request)
    except Exception as e:
        logger.error(f"Availability check failed: {e}", exc_info=True)
        # Avoid leaking details; Orchestrator will surface a friendly message
        raise


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment (Internal)",
    description=(
        "Book an appointment in LexiqAI-native scheduling. "
        "Intended for internal service calls (e.g., Cognitive Orchestrator tools)."
    ),
    dependencies=[InternalAuthDep],
    include_in_schema=False,
)
async def book_appointment(request: AppointmentCreateRequest) -> AppointmentResponse:
    """Book an appointment (idempotent via idempotency_key)."""
    async with get_session_context() as session:
        service = get_appointments_service_for_session(session)
        return await service.book_appointment(request)


