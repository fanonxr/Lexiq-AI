"""Webhook processing Celery tasks."""

import logging
from typing import Any, Dict

from celery import shared_task

from integration_worker.database.session import get_session
from integration_worker.services.outlook_service import OutlookService
from integration_worker.utils.async_helpers import run_async
from integration_worker.utils.errors import WebhookError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="integration_worker.tasks.webhook_processing.process_outlook_notification",
    max_retries=3,
    default_retry_delay=30,  # Shorter delay for webhook events (30s)
)
def process_outlook_notification(
    self,
    integration_id: str,
    change_type: str,
    resource: str,
    resource_data: Dict[str, Any],
) -> dict:
    """
    Process Outlook calendar change notification from Microsoft Graph webhook.
    
    This task is triggered when a calendar event is created, updated, or deleted.
    It syncs the specific event instead of doing a full calendar sync.
    
    Args:
        integration_id: Calendar integration ID (from webhook clientState)
        change_type: Type of change (created, updated, deleted)
        resource: Resource URL (e.g., /me/events/AAMkAG...)
        resource_data: Resource data from webhook (may be empty)
    
    Returns:
        dict with processing result
    """
    try:
        # Extract event ID from resource URL
        # Resource format: "/me/events/AAMkAG..." or similar
        event_id = resource.split("/")[-1] if "/" in resource else resource
        
        logger.info(
            f"Processing Outlook notification: {change_type} for event {event_id} "
            f"(integration {integration_id})"
        )
        
        async def _process():
            async with get_session() as session:
                from integration_worker.database.repositories import (
                    CalendarIntegrationRepository,
                    AppointmentsRepository,
                )
                
                repo = CalendarIntegrationRepository(session)
                integration = await repo.get_by_id(integration_id)
                
                if not integration:
                    raise WebhookError(f"Integration {integration_id} not found")
                
                if change_type in ["created", "updated"]:
                    # Optimized: Sync only the specific event (faster than full sync)
                    outlook_service = OutlookService(session)
                    
                    try:
                        result = await outlook_service.sync_single_event(
                            integration_id,
                            event_id,
                        )
                        
                        logger.info(
                            f"Processed {change_type} notification for event {event_id}: "
                            f"{result.appointments_synced} created, "
                            f"{result.appointments_updated} updated"
                        )
                        
                        return {
                            "success": result.success,
                            "change_type": change_type,
                            "event_id": event_id,
                            "appointments_synced": result.appointments_synced,
                            "appointments_updated": result.appointments_updated,
                            "errors": result.errors,
                        }
                    except Exception as sync_error:
                        # Fallback to full sync if single event sync fails
                        # (e.g., event not found, API error, etc.)
                        logger.warning(
                            f"Single event sync failed for {event_id}, falling back to full sync: {sync_error}"
                        )
                        
                        try:
                            result = await outlook_service.sync_calendar(integration_id)
                            
                            logger.info(
                                f"Fallback full sync completed: {result.appointments_synced} appointments synced"
                            )
                            
                            return {
                                "success": result.success,
                                "change_type": change_type,
                                "event_id": event_id,
                                "appointments_synced": result.appointments_synced,
                                "appointments_updated": result.appointments_updated,
                                "fallback_used": True,
                                "errors": result.errors,
                            }
                        except Exception as fallback_error:
                            logger.error(
                                f"Both single event and full sync failed for event {event_id}: {fallback_error}",
                                exc_info=True,
                            )
                            raise
                    
                elif change_type == "deleted":
                    # For deleted events, mark appointment as cancelled
                    outlook_service = OutlookService(session)
                    
                    try:
                        cancelled = await outlook_service.delete_synced_event(
                            integration_id,
                            event_id,
                        )
                        
                        return {
                            "success": True,
                            "change_type": change_type,
                            "event_id": event_id,
                            "appointment_cancelled": cancelled,
                        }
                    except Exception as delete_error:
                        logger.error(
                            f"Error marking appointment as cancelled for event {event_id}: {delete_error}",
                            exc_info=True,
                        )
                        # Don't fail the webhook - log and continue
                        return {
                            "success": False,
                            "change_type": change_type,
                            "event_id": event_id,
                            "appointment_cancelled": False,
                            "error": str(delete_error),
                        }
                else:
                    logger.warning(f"Unknown change type: {change_type}")
                    return {
                        "success": False,
                        "change_type": change_type,
                        "error": f"Unknown change type: {change_type}",
                    }
        
        result = run_async(_process())
        
        logger.info(f"Successfully processed Outlook notification: {result}")
        
        return result
        
    except WebhookError as exc:
        logger.error(
            f"Webhook error processing notification: {exc}",
            exc_info=True,
        )
        # Retry with shorter delay for webhook events
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(
            f"Unexpected error processing Outlook notification: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

