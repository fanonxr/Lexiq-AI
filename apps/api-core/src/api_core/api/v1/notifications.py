"""Notification endpoints (LexiqAI-native outbox)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from api_core.auth.internal_service import InternalAuthDep
from api_core.database.session import get_session_context
from api_core.models.notifications import NotificationCreateRequest, NotificationResponse
from api_core.services.notifications_service import get_notifications_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create notification (Internal)",
    description=(
        "Create a LexiqAI-native notification outbox record. "
        "Intended for internal service calls (e.g., Cognitive Orchestrator tools)."
    ),
    dependencies=[InternalAuthDep],
    include_in_schema=False,
)
async def create_notification(request: NotificationCreateRequest) -> NotificationResponse:
    """
    Create a notification (idempotent via idempotency_key).
    
    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Cognitive Orchestrator (tool: send_notification)
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    async with get_session_context() as session:
        service = get_notifications_service(session)
        return await service.create_notification(request)


