"""Appointments endpoints (LexiqAI-native scheduling).

NOTE: For Phase 5 tool execution, these endpoints are primarily used by the Cognitive Orchestrator
as internal service calls.

User-facing endpoints have been added for Phase 5 frontend integration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.internal_service import InternalAuthDep
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.appointments import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AvailabilityRequest,
    AvailabilityResponse,
)
from api_core.services.appointments_service import get_appointments_service, get_appointments_service_for_session
from api_core.services.calendar_integration_service import CalendarIntegrationService

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
    """
    Return candidate slots in the requested window.

    This MVP implementation applies simple business-hour rules (Mon–Fri, 9–5 local time).
    
    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Cognitive Orchestrator (tool: check_availability)
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
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
    """
    Book an appointment (idempotent via idempotency_key).
    
    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Cognitive Orchestrator (tool: book_appointment)
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    async with get_session_context() as session:
        service = get_appointments_service_for_session(session)
        return await service.book_appointment(request)


# User-facing endpoints for Phase 5

# Frontend-compatible models
class FrontendAppointment(BaseModel):
    """Frontend-compatible appointment model."""
    
    id: str = Field(..., description="Appointment ID")
    clientName: str = Field(..., description="Client name")
    clientEmail: Optional[str] = Field(None, description="Client email")
    dateTime: datetime = Field(..., description="Appointment date and time")
    type: str = Field(..., description="Appointment type: consultation, follow-up, meeting, other")
    status: str = Field(..., description="Appointment status: confirmed, proposed, rescheduled, cancelled")
    description: Optional[str] = Field(None, description="Appointment description/notes")


class AppointmentsListResponse(BaseModel):
    """Response model for appointments list."""
    
    appointments: List[FrontendAppointment] = Field(..., description="List of appointments")


class IntegrationStatus(BaseModel):
    """Integration status model."""
    
    type: str = Field(..., description="Integration type: outlook or google")
    isConnected: bool = Field(..., description="Whether the integration is connected")
    lastSynced: Optional[datetime] = Field(None, description="Last sync timestamp")
    error: Optional[str] = Field(None, description="Error message if disconnected")


class IntegrationStatusResponse(BaseModel):
    """Response model for integration status."""
    
    integrations: List[IntegrationStatus] = Field(..., description="List of integration statuses")


class SyncAppointmentsRequest(BaseModel):
    """Request model for syncing appointments."""
    
    integration: Optional[str] = Field(None, description="Integration type to sync (outlook/google), syncs all if not provided")


class SyncAppointmentsResponse(BaseModel):
    """Response model for sync operation."""
    
    success: bool = Field(..., description="Whether sync was successful")
    appointmentsSynced: int = Field(..., description="Number of appointments synced")
    lastSynced: datetime = Field(..., description="Last sync timestamp")
    message: Optional[str] = Field(None, description="Status message")
    taskIds: Optional[List[str]] = Field(default=None, description="Celery task IDs (if async)")


class UpdateAppointmentRequest(BaseModel):
    """Request model for updating an appointment."""
    
    updates: dict = Field(..., description="Partial appointment data to update")


class UpdateAppointmentResponse(BaseModel):
    """Response model for appointment update."""
    
    appointment: FrontendAppointment = Field(..., description="Updated appointment")


class CancelAppointmentRequest(BaseModel):
    """Request model for cancelling an appointment."""
    
    reason: Optional[str] = Field(None, description="Cancellation reason")


class CancelAppointmentResponse(BaseModel):
    """Response model for appointment cancellation."""
    
    success: bool = Field(..., description="Whether cancellation was successful")
    appointment: FrontendAppointment = Field(..., description="Cancelled appointment")
    message: Optional[str] = Field(None, description="Status message")


def _appointment_to_frontend(appointment) -> FrontendAppointment:
    """Convert backend Appointment model to frontend format."""
    # Map backend status to frontend status
    status_mapping = {
        "booked": "confirmed",
        "confirmed": "confirmed",
        "proposed": "proposed",
        "rescheduled": "rescheduled",
        "cancelled": "cancelled",
    }
    frontend_status = status_mapping.get(appointment.status, "confirmed")
    
    # Map title to type (simple mapping - can be enhanced)
    type_mapping = {
        "consultation": "consultation",
        "follow-up": "follow-up",
        "followup": "follow-up",
        "meeting": "meeting",
    }
    appointment_type = "other"
    if appointment.title:
        title_lower = appointment.title.lower()
        for key, value in type_mapping.items():
            if key in title_lower:
                appointment_type = value
                break
    
    return FrontendAppointment(
        id=appointment.id,
        clientName=appointment.contact_full_name,
        clientEmail=appointment.contact_email,
        dateTime=appointment.start_at,
        type=appointment_type,
        status=frontend_status,
        description=appointment.notes or appointment.title,
    )


@router.get(
    "",
    response_model=AppointmentsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List appointments",
    description="List appointments for the authenticated user, optionally filtered by date range and source.",
)
async def list_appointments(
    startDate: Optional[datetime] = Query(None, description="Start date filter (ISO8601)"),
    endDate: Optional[datetime] = Query(None, description="End date filter (ISO8601)"),
    clientsOnly: bool = Query(
        True,
        description="If true, only return appointments created through LexiqAI (exclude calendar events). Defaults to true.",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    List appointments for the authenticated user.
    
    By default, only shows client appointments (created through LexiqAI).
    Set clientsOnly=false to see all appointments including calendar events.
    """
    try:
        async with get_session_context() as session:
            service = get_appointments_service_for_session(session)
            
            # Get firm_id from user if available
            firm_id = None
            if hasattr(current_user, "firm_id") and current_user.firm_id:
                firm_id = current_user.firm_id
            
            appointments = await service.get_user_appointments(
                user_id=current_user.user_id,
                firm_id=firm_id,
                start_date=startDate,
                end_date=endDate,
                clients_only=clientsOnly,
                skip=skip,
                limit=limit,
            )
            
            frontend_appointments = [_appointment_to_frontend(apt) for apt in appointments]
            
            return AppointmentsListResponse(appointments=frontend_appointments)
            
    except Exception as e:
        logger.error(f"Error listing appointments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve appointments",
        ) from e


@router.get(
    "/integrations",
    response_model=IntegrationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get integration status",
    description="Get status of calendar integrations (Outlook/Google Calendar).",
)
async def get_integration_status(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Get integration status for calendar integrations."""
    try:
        async with get_session_context() as session:
            service = CalendarIntegrationService(session)
            integrations = await service.repository.get_by_user(current_user.user_id)

            # Build response
            statuses = []
            connected_types = set()
            for integration in integrations:
                statuses.append(
                    IntegrationStatus(
                        type=integration.integration_type,
                        isConnected=integration.is_active,
                        lastSynced=integration.last_synced_at if integration.last_synced_at else None,
                        error=integration.sync_error,
                    )
                )
                connected_types.add(integration.integration_type)

            # Add placeholder for disconnected integrations
            if "outlook" not in connected_types:
                statuses.append(
                    IntegrationStatus(
                        type="outlook",
                        isConnected=False,
                        lastSynced=None,
                        error=None,
                    )
                )
            if "google" not in connected_types:
                statuses.append(
                    IntegrationStatus(
                        type="google",
                        isConnected=False,
                        lastSynced=None,
                        error=None,
                    )
                )

            return IntegrationStatusResponse(integrations=statuses)

    except Exception as e:
        logger.error(f"Error getting integration status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integration status",
        ) from e


@router.post(
    "/sync",
    response_model=SyncAppointmentsResponse,
    status_code=status.HTTP_202_ACCEPTED,  # Changed from 200 to 202 (Accepted - async processing)
    summary="Sync appointments (async)",
    description="Trigger async calendar sync for all connected integrations. Returns immediately with task IDs.",
)
async def sync_appointments(
    request: SyncAppointmentsRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Trigger calendar sync as background task.
    
    This endpoint triggers async Celery tasks and returns immediately.
    The actual sync happens in the background via integration-worker.
    """
    try:
        async with get_session_context() as session:
            service = CalendarIntegrationService(session)
            
            # Determine which integrations to sync
            integration_types = []
            if request.integration:
                integration_types = [request.integration]
            else:
                # Sync all connected integrations
                integrations = await service.repository.get_by_user(current_user.user_id)
                integration_types = [intg.integration_type for intg in integrations if intg.is_active]
            
            # Trigger async tasks for each integration using Celery client
            task_ids = []
            triggered_count = 0
            
            try:
                from api_core.celery_client import send_calendar_sync_task
                
                for integration_type in integration_types:
                    integration = await service.repository.get_by_user_and_type(
                        current_user.user_id,
                        integration_type,
                    )
                    if integration:
                        task_id = send_calendar_sync_task(
                            integration_type=integration_type,
                            integration_id=str(integration.id),
                        )
                        task_ids.append(task_id)
                        triggered_count += 1
                        logger.info(
                            f"Triggered {integration_type} sync task {task_id} for user {current_user.user_id}"
                        )
                
                from datetime import timezone
                return SyncAppointmentsResponse(
                    success=True,
                    appointmentsSynced=0,  # Will be updated by background tasks
                    lastSynced=datetime.now(timezone.utc),
                    message=f"Sync started for {triggered_count} integration(s). This may take a few moments.",
                    taskIds=task_ids if task_ids else None,
                )
                
            except (ImportError, RuntimeError) as e:
                # Fallback: If Celery is not available, run sync synchronously
                # This happens if Celery is not installed or Redis is not accessible
                logger.warning(
                    f"Celery client not available, running sync synchronously: {e}. "
                )
                
                total_synced = 0
                from datetime import timezone
                last_synced = datetime.now(timezone.utc)
                
                # Sync each integration type synchronously
                for integration_type in integration_types:
                    integration = await service.repository.get_by_user_and_type(
                        current_user.user_id,
                        integration_type,
                    )
                    if integration:
                        if integration_type == "outlook":
                            count = await service.sync_outlook_calendar(integration)
                            total_synced += count
                            if integration.last_synced_at:
                                last_synced = integration.last_synced_at
                        # Add Google Calendar sync here when implemented
                        # elif integration_type == "google":
                        #     count = await service.sync_google_calendar(integration)
                        #     total_synced += count
                
                return SyncAppointmentsResponse(
                    success=True,
                    appointmentsSynced=total_synced,
                    lastSynced=last_synced,
                    message=f"Synced {total_synced} appointment(s) from {len(integration_types)} integration(s)",
                )
        
    except Exception as e:
        logger.error(f"Error syncing appointments: {e}", exc_info=True)
        error_message = str(e)
        # Provide more helpful error messages
        if "token" in error_message.lower() or "authentication" in error_message.lower():
            error_message = "Authentication failed. Please reconnect your calendar integration."
        elif "not found" in error_message.lower():
            error_message = "Calendar integration not found. Please reconnect your calendar."
        elif "permission" in error_message.lower() or "access" in error_message.lower():
            error_message = "Insufficient permissions. Please reconnect your calendar with proper permissions."
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync appointments: {error_message}",
        ) from e


@router.put(
    "/{appointment_id}",
    response_model=UpdateAppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update appointment",
    description="Update an appointment (date, time, status, description).",
)
async def update_appointment(
    appointment_id: str,
    request: UpdateAppointmentRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Update an appointment."""
    try:
        async with get_session_context() as session:
            service = get_appointments_service_for_session(session)
            
            updates = request.updates
            
            # Map frontend fields to backend fields
            title = updates.get("title") or updates.get("description")
            notes = updates.get("description") or updates.get("notes")
            status = updates.get("status")
            date_time = updates.get("dateTime")
            
            # Convert dateTime to start_at and end_at if provided
            start_at = None
            end_at = None
            if date_time:
                if isinstance(date_time, str):
                    date_time = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
                start_at = date_time
                # Default duration: 30 minutes (can be enhanced)
                from datetime import timedelta
                end_at = start_at + timedelta(minutes=30)
            
            appointment = await service.update_appointment(
                appointment_id=appointment_id,
                user_id=current_user.user_id,
                title=title,
                notes=notes,
                status=status,
                start_at=start_at,
                end_at=end_at,
            )
            
            frontend_appointment = _appointment_to_frontend(appointment)
            
            return UpdateAppointmentResponse(appointment=frontend_appointment)
            
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating appointment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update appointment",
        ) from e


@router.post(
    "/{appointment_id}/cancel",
    response_model=CancelAppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel appointment",
    description="Cancel an appointment.",
)
async def cancel_appointment(
    appointment_id: str,
    request: CancelAppointmentRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Cancel an appointment."""
    try:
        async with get_session_context() as session:
            service = get_appointments_service_for_session(session)
            
            appointment = await service.cancel_appointment(
                appointment_id=appointment_id,
                user_id=current_user.user_id,
                reason=request.reason,
            )
            
            frontend_appointment = _appointment_to_frontend(appointment)
            
            return CancelAppointmentResponse(
                success=True,
                appointment=frontend_appointment,
                message="Appointment cancelled successfully",
            )
            
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel appointment",
        ) from e


class AppointmentSourceMappingResponse(BaseModel):
    """Response model for appointment source mappings."""
    
    sources: dict[str, str] = Field(..., description="Map of appointment IDs to source calendar (outlook/google)")


@router.get(
    "/sources",
    response_model=AppointmentSourceMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get appointment sources",
    description="Get mapping of appointment IDs to their source calendar (outlook/google).",
)
async def get_appointment_sources(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Get appointment source mappings."""
    try:
        async with get_session_context() as session:
            from sqlalchemy import select
            from api_core.database.models import Appointment, CalendarIntegration
            
            # Query appointments with their source calendar integration
            # Join with calendar_integrations to get the integration_type
            query = (
                select(
                    Appointment.id,
                    CalendarIntegration.integration_type,
                )
                .outerjoin(
                    CalendarIntegration,
                    Appointment.source_calendar_id == CalendarIntegration.id,
                )
                .where(Appointment.created_by_user_id == current_user.user_id)
            )
            
            result = await session.execute(query)
            rows = result.all()
            
            # Build mapping of appointment ID to integration type
            sources: dict[str, str] = {}
            for appointment_id, integration_type in rows:
                if integration_type:
                    # Map integration_type to source string
                    sources[appointment_id] = integration_type  # "outlook" or "google"
                # If no integration_type, appointment is from LexiqAI (not synced from calendar)
                # We don't include it in the mapping, so it will use the default styling
            
            return AppointmentSourceMappingResponse(sources=sources)
        
    except Exception as e:
        logger.error(f"Error getting appointment sources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve appointment sources",
        ) from e


