"""Webhook subscription management Celery tasks.

These tasks handle creation, renewal, and deletion of webhook subscriptions
for calendar integrations.
"""

import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

from integration_worker.database.session import get_session
from integration_worker.services.webhook_service import WebhookService
from integration_worker.services.outlook_service import OutlookService
from integration_worker.utils.async_helpers import run_async
from integration_worker.utils.errors import WebhookError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="integration_worker.tasks.webhook_management.create_webhook_subscription",
    max_retries=3,
    default_retry_delay=60,
)
def create_webhook_subscription(
    self,
    integration_id: str,
) -> dict:
    """
    Create webhook subscription for a calendar integration.
    
    Args:
        integration_id: Calendar integration ID
    
    Returns:
        dict with subscription details
    """
    try:
        async def _create():
            async with get_session() as session:
                from integration_worker.database.repositories import (
                    CalendarIntegrationRepository,
                )
                
                repo = CalendarIntegrationRepository(session)
                integration = await repo.get_by_id(integration_id)
                
                if not integration:
                    raise WebhookError(f"Integration {integration_id} not found")
                
                if integration.integration_type == "outlook":
                    # Get valid access token
                    outlook_service = OutlookService(session)
                    access_token = await outlook_service.get_valid_access_token(integration)
                    
                    # Create subscription
                    webhook_service = WebhookService()
                    subscription = await webhook_service.create_outlook_subscription(
                        integration,
                        access_token
                    )
                    
                    # Update integration with subscription details
                    integration.webhook_subscription_id = subscription['id']
                    integration.webhook_subscription_expires_at = datetime.fromisoformat(
                        subscription['expirationDateTime'].replace('Z', '+00:00')
                    )
                    integration.webhook_notification_url = subscription.get('notificationUrl')
                    await session.flush()
                    
                    return {
                        "success": True,
                        "integration_id": integration_id,
                        "subscription_id": subscription['id'],
                        "expires_at": subscription['expirationDateTime'],
                    }
                elif integration.integration_type == "google":
                    # Google Calendar webhooks (Phase 5)
                    logger.info(f"Google Calendar webhooks not yet implemented (Phase 5)")
                    return {
                        "success": False,
                        "integration_id": integration_id,
                        "error": "Google Calendar webhooks not yet implemented",
                    }
                else:
                    raise WebhookError(f"Unknown integration type: {integration.integration_type}")
        
        result = run_async(_create())
        
        logger.info(
            f"Created webhook subscription for integration {integration_id}: {result}"
        )
        
        return result
        
    except WebhookError as exc:
        logger.error(
            f"Webhook error creating subscription for {integration_id}: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    except Exception as exc:
        logger.error(
            f"Unexpected error creating webhook subscription: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    name="integration_worker.tasks.webhook_management.renew_expiring_subscriptions",
)
def renew_expiring_subscriptions() -> dict:
    """
    Renew webhook subscriptions that are expiring soon (< 12 hours).
    
    This task is triggered by Celery Beat (can be scheduled hourly).
    
    Returns:
        dict with renewal statistics
    """
    async def _renew_all():
        async with get_session() as session:
            from integration_worker.database.repositories import (
                CalendarIntegrationRepository,
            )
            from sqlalchemy import select, and_
            
            try:
                from api_core.database.models import CalendarIntegration
            except ImportError:
                raise ImportError("Cannot import api_core models")
            
            repo = CalendarIntegrationRepository(session)
            
            # Find integrations with subscriptions expiring < 12 hours
            expiring_soon = datetime.now(timezone.utc) + timedelta(hours=12)
            
            # Query integrations with webhook subscriptions expiring soon
            result = await session.execute(
                select(CalendarIntegration)
                .where(and_(
                    CalendarIntegration.is_active == True,
                    CalendarIntegration.webhook_subscription_id.isnot(None),
                    CalendarIntegration.webhook_subscription_expires_at.isnot(None),
                    CalendarIntegration.webhook_subscription_expires_at <= expiring_soon,
                ))
            )
            integrations = list(result.scalars().all())
            
            logger.info(f"Found {len(integrations)} webhook subscriptions to renew")
            
            renewed = 0
            errors = 0
            
            for integration in integrations:
                try:
                    if integration.integration_type == "outlook":
                        outlook_service = OutlookService(session)
                        access_token = await outlook_service.get_valid_access_token(integration)
                        
                        webhook_service = WebhookService()
                        subscription = await webhook_service.renew_outlook_subscription(
                            integration.webhook_subscription_id,
                            access_token
                        )
                        
                        # Update expiration in database
                        integration.webhook_subscription_expires_at = datetime.fromisoformat(
                            subscription['expirationDateTime'].replace('Z', '+00:00')
                        )
                        await session.flush()
                        
                        renewed += 1
                        logger.info(f"Renewed webhook subscription for integration {integration.id}")
                    elif integration.integration_type == "google":
                        # Google Calendar (Phase 5)
                        logger.info(f"Skipping Google webhook renewal for {integration.id} (Phase 5)")
                        pass
                except Exception as e:
                    logger.error(
                        f"Failed to renew webhook subscription for {integration.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
            
            return {"renewed": renewed, "errors": errors}
    
    result = run_async(_renew_all())
    
    logger.info(
        f"Renewed {result['renewed']} webhook subscriptions ({result['errors']} errors)"
    )
    
    return result


@shared_task(
    bind=True,
    name="integration_worker.tasks.webhook_management.delete_webhook_subscription",
    max_retries=3,
)
def delete_webhook_subscription(
    self,
    integration_id: str,
    subscription_id: str,
) -> dict:
    """
    Delete webhook subscription for a calendar integration.
    
    Called when user disconnects calendar integration.
    
    Args:
        integration_id: Calendar integration ID
        subscription_id: Subscription ID to delete
    
    Returns:
        dict with deletion status
    """
    try:
        async def _delete():
            async with get_session() as session:
                from integration_worker.database.repositories import (
                    CalendarIntegrationRepository,
                )
                
                repo = CalendarIntegrationRepository(session)
                integration = await repo.get_by_id(integration_id)
                
                if not integration:
                    logger.warning(f"Integration {integration_id} not found, cannot delete subscription")
                    return {
                        "success": False,
                        "error": "Integration not found",
                    }
                
                if integration.integration_type == "outlook":
                    outlook_service = OutlookService(session)
                    access_token = await outlook_service.get_valid_access_token(integration)
                    
                    webhook_service = WebhookService()
                    await webhook_service.delete_outlook_subscription(
                        subscription_id,
                        access_token
                    )
                    
                    # Clear subscription fields in database
                    integration.webhook_subscription_id = None
                    integration.webhook_subscription_expires_at = None
                    integration.webhook_notification_url = None
                    await session.flush()
                    
                    return {
                        "success": True,
                        "integration_id": integration_id,
                        "subscription_id": subscription_id,
                    }
                elif integration.integration_type == "google":
                    # Google Calendar (Phase 5)
                    logger.info(f"Google Calendar webhooks not yet implemented (Phase 5)")
                    return {
                        "success": False,
                        "error": "Google Calendar webhooks not yet implemented",
                    }
        
        result = run_async(_delete())
        
        logger.info(f"Deleted webhook subscription: {result}")
        
        return result
        
    except Exception as exc:
        logger.error(
            f"Error deleting webhook subscription: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

