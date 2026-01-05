"""Calendar sync Celery tasks."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from celery import shared_task

from integration_worker.database.session import get_session
from integration_worker.services.outlook_service import OutlookService
from integration_worker.services.google_service import GoogleService
from integration_worker.utils.async_helpers import run_async
from integration_worker.utils.errors import SyncError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="integration_worker.tasks.calendar_sync.sync_outlook_calendar",
    max_retries=3,
    default_retry_delay=60,
)
def sync_outlook_calendar(
    self,
    integration_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Sync Outlook calendar for a specific integration.
    
    Args:
        integration_id: Calendar integration ID
        start_date: ISO format start date (optional)
        end_date: ISO format end date (optional)
    
    Returns:
        Sync result dict with count and status
    """
    try:
        # Parse dates if provided
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        # Run sync in async context
        async def _run_sync():
            async with get_session() as session:
                service = OutlookService(session)
                return await service.sync_calendar(integration_id, start, end)
        
        result = run_async(_run_sync())
        
        logger.info(
            f"Synced {result.appointments_synced} appointments "
            f"for integration {integration_id}"
        )
        
        return {
            "success": result.success,
            "integration_id": integration_id,
            "appointments_synced": result.appointments_synced,
            "appointments_updated": result.appointments_updated,
            "appointments_deleted": result.appointments_deleted,
            "total_changes": result.total_changes,
            "errors": result.errors,
        }
        
    except SyncError as exc:
        logger.error(
            f"Sync error for Outlook calendar {integration_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(
            f"Unexpected error syncing Outlook calendar {integration_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    name="integration_worker.tasks.calendar_sync.sync_all_calendars",
)
def sync_all_calendars() -> dict:
    """
    Sync all active calendar integrations (scheduled task).
    
    This task is triggered by Celery Beat every 15 minutes.
    """
    async def _run_sync_all():
        async with get_session() as session:
            from integration_worker.database.repositories import (
                CalendarIntegrationRepository,
            )
            
            repo = CalendarIntegrationRepository(session)
            integrations = await repo.get_all_active()
            
            synced = 0
            errors = 0
            
            for integration in integrations:
                try:
                    # Trigger async task for each integration
                    if integration.integration_type == "outlook":
                        sync_outlook_calendar.delay(str(integration.id))
                        synced += 1
                    elif integration.integration_type == "google":
                        sync_google_calendar.delay(str(integration.id))
                        synced += 1
                except Exception as e:
                    logger.error(
                        f"Failed to trigger sync for {integration.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
            
            return {"synced": synced, "errors": errors}
    
    result = run_async(_run_sync_all())
    
    logger.info(
        f"Triggered sync for {result['synced']} integrations "
        f"({result['errors']} errors)"
    )
    
    return result


@shared_task(
    bind=True,
    name="integration_worker.tasks.calendar_sync.sync_google_calendar",
    max_retries=3,
    default_retry_delay=60,
)
def sync_google_calendar(
    self,
    integration_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    Sync Google Calendar for a specific integration.
    
    Args:
        integration_id: Calendar integration ID
        start_date: ISO format start date (optional)
        end_date: ISO format end date (optional)
    
    Returns:
        Sync result dict with count and status
    """
    try:
        # Parse dates if provided
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        # Run sync in async context
        async def _run_sync():
            async with get_session() as session:
                service = GoogleService(session)
                return await service.sync_calendar(integration_id, start, end)
        
        result = run_async(_run_sync())
        
        logger.info(
            f"Synced {result.appointments_synced} appointments "
            f"for Google Calendar integration {integration_id}"
        )
        
        return {
            "success": result.success,
            "integration_id": integration_id,
            "appointments_synced": result.appointments_synced,
            "appointments_updated": result.appointments_updated,
            "appointments_deleted": result.appointments_deleted,
            "total_changes": result.total_changes,
            "errors": result.errors,
        }
        
    except SyncError as exc:
        logger.error(
            f"Sync error for Google Calendar {integration_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(
            f"Unexpected error syncing Google Calendar {integration_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

