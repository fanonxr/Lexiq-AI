"""Internal job endpoints (triggered by workers; require internal API key)."""

import logging

from fastapi import APIRouter, Depends, status

from api_core.auth.internal_service import InternalAuthDep
from api_core.database.session import get_session_context
from api_core.services.orphan_cleanup_service import OrphanCleanupService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "/cleanup-orphaned-resources",
    status_code=status.HTTP_200_OK,
    summary="Cleanup orphaned resources",
    description=(
        "Finds and terminates orphaned resources: Twilio subaccounts not tied to any firm, "
        "pool numbers assigned to deleted firms. Intended to be called periodically by integration-worker. "
        "Requires X-Internal-API-Key."
    ),
    dependencies=[InternalAuthDep],
)
async def cleanup_orphaned_resources():
    """
    Run orphan cleanup (Twilio subaccounts, phone number pool).

    Returns counts of resources closed/reclaimed.
    """
    async with get_session_context() as session:
        service = OrphanCleanupService(session)
        result = await service.run()
        await session.commit()
    return result
