"""Lead/intake endpoints (LexiqAI-native)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status

from api_core.auth.internal_service import InternalAuthDep
from api_core.database.session import get_session_context
from api_core.models.leads import LeadCreateRequest, LeadResponse
from api_core.services.leads_service import get_leads_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead (Internal)",
    description=(
        "Create a LexiqAI-native lead/intake record. "
        "Intended for internal service calls (e.g., Cognitive Orchestrator tools)."
    ),
    dependencies=[InternalAuthDep],
    include_in_schema=False,
)
async def create_lead(request: LeadCreateRequest) -> LeadResponse:
    """
    Create a lead (idempotent via idempotency_key).
    
    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Cognitive Orchestrator (tool: create_lead)
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    async with get_session_context() as session:
        service = get_leads_service(session)
        return await service.create_lead(request)


