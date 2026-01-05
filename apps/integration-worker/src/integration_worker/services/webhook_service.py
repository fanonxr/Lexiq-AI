"""Webhook subscription management for Microsoft Graph and Google Calendar.

This service manages webhook subscriptions for real-time calendar event notifications.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from integration_worker.config import get_settings
from integration_worker.utils.errors import WebhookError, ExternalAPIError

# Import models from api-core (shared database)
try:
    from api_core.database.models import CalendarIntegration
except ImportError:
    raise ImportError(
        "Cannot import api_core models. "
        "Ensure api-core is in PYTHONPATH or installed as a package."
    )

logger = logging.getLogger(__name__)
settings = get_settings()


class WebhookService:
    """Manage webhook subscriptions for calendar integrations."""
    
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    SUBSCRIPTION_EXPIRY_DAYS = 3  # Microsoft Graph max is 3 days
    RENEWAL_THRESHOLD_HOURS = 12  # Renew when < 12 hours remaining
    
    async def create_outlook_subscription(
        self,
        integration: CalendarIntegration,
        access_token: str,
    ) -> dict:
        """
        Create Microsoft Graph webhook subscription for calendar events.
        
        Args:
            integration: Calendar integration
            access_token: Valid access token for Microsoft Graph
        
        Returns:
            dict with subscription details (id, expirationDateTime, etc.)
        
        Raises:
            WebhookError: If subscription creation fails
            ExternalAPIError: If Microsoft Graph API call fails
        """
        try:
            # Webhook endpoint URL (must be publicly accessible)
            notification_url = f"{settings.webhook_base_url}/webhooks/outlook/notifications"
            
            # Calculate expiration (max 3 days for Graph API)
            expiration_datetime = (
                datetime.now(timezone.utc) + timedelta(days=self.SUBSCRIPTION_EXPIRY_DAYS)
            ).isoformat()
            
            # Subscription payload
            subscription_data = {
                "changeType": "created,updated,deleted",
                "notificationUrl": notification_url,
                "resource": "/me/events",  # Subscribe to all calendar events
                "expirationDateTime": expiration_datetime,
                "clientState": str(integration.id),  # Used to verify webhook authenticity
            }
            
            logger.info(
                f"Creating Outlook webhook subscription for integration {integration.id} "
                f"(notification_url={notification_url})"
            )
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.GRAPH_API_URL}/subscriptions",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=subscription_data,
                )
                
                if response.status_code != 201:
                    error_msg = f"Failed to create subscription: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    raise ExternalAPIError(error_msg)
                
                subscription = response.json()
                
                logger.info(
                    f"Created Outlook webhook subscription {subscription['id']} "
                    f"for integration {integration.id}, expires at {subscription['expirationDateTime']}"
                )
                
                return subscription
                
        except httpx.HTTPError as e:
            error_msg = f"HTTP error creating Outlook webhook subscription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExternalAPIError(error_msg) from e
        except Exception as e:
            error_msg = f"Error creating Outlook webhook subscription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise WebhookError(error_msg) from e
    
    async def renew_outlook_subscription(
        self,
        subscription_id: str,
        access_token: str,
    ) -> dict:
        """
        Renew Outlook webhook subscription (before it expires).
        
        Microsoft Graph subscriptions expire after max 3 days and must be renewed.
        
        Args:
            subscription_id: Existing subscription ID
            access_token: Valid access token for Microsoft Graph
        
        Returns:
            dict with updated subscription details
        
        Raises:
            WebhookError: If renewal fails
            ExternalAPIError: If Microsoft Graph API call fails
        """
        try:
            # Calculate new expiration
            new_expiration = (
                datetime.now(timezone.utc) + timedelta(days=self.SUBSCRIPTION_EXPIRY_DAYS)
            ).isoformat()
            
            logger.info(f"Renewing Outlook webhook subscription {subscription_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{self.GRAPH_API_URL}/subscriptions/{subscription_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={"expirationDateTime": new_expiration},
                )
                
                if response.status_code != 200:
                    error_msg = f"Failed to renew subscription: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    raise ExternalAPIError(error_msg)
                
                subscription = response.json()
                
                logger.info(
                    f"Renewed Outlook webhook subscription {subscription_id}, "
                    f"new expiration: {subscription['expirationDateTime']}"
                )
                
                return subscription
                
        except httpx.HTTPError as e:
            error_msg = f"HTTP error renewing Outlook webhook subscription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExternalAPIError(error_msg) from e
        except Exception as e:
            error_msg = f"Error renewing Outlook webhook subscription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise WebhookError(error_msg) from e
    
    async def delete_outlook_subscription(
        self,
        subscription_id: str,
        access_token: str,
    ) -> None:
        """
        Delete Outlook webhook subscription.
        
        Called when user disconnects calendar integration.
        
        Args:
            subscription_id: Subscription ID to delete
            access_token: Valid access token for Microsoft Graph
        
        Raises:
            WebhookError: If deletion fails
            ExternalAPIError: If Microsoft Graph API call fails
        """
        try:
            logger.info(f"Deleting Outlook webhook subscription {subscription_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.GRAPH_API_URL}/subscriptions/{subscription_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                
                # 204 No Content or 404 Not Found are both acceptable
                # (404 means subscription already deleted or expired)
                if response.status_code not in (204, 404):
                    error_msg = f"Failed to delete subscription: {response.status_code} {response.text}"
                    logger.error(error_msg)
                    raise ExternalAPIError(error_msg)
                
                logger.info(f"Deleted Outlook webhook subscription {subscription_id}")
                
        except httpx.HTTPError as e:
            error_msg = f"HTTP error deleting Outlook webhook subscription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExternalAPIError(error_msg) from e
        except Exception as e:
            error_msg = f"Error deleting Outlook webhook subscription: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise WebhookError(error_msg) from e
    
    async def get_subscription_status(
        self,
        subscription_id: str,
        access_token: str,
    ) -> Optional[dict]:
        """
        Get current status of a webhook subscription.
        
        Args:
            subscription_id: Subscription ID to check
            access_token: Valid access token for Microsoft Graph
        
        Returns:
            dict with subscription details or None if not found
        
        Raises:
            ExternalAPIError: If Microsoft Graph API call fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.GRAPH_API_URL}/subscriptions/{subscription_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                
                if response.status_code == 404:
                    logger.warning(f"Subscription {subscription_id} not found (may have expired)")
                    return None
                
                if response.status_code != 200:
                    error_msg = f"Failed to get subscription status: {response.status_code}"
                    logger.error(error_msg)
                    raise ExternalAPIError(error_msg)
                
                return response.json()
                
        except httpx.HTTPError as e:
            error_msg = f"HTTP error getting subscription status: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExternalAPIError(error_msg) from e
    
    def should_renew_subscription(self, expiration_datetime: str) -> bool:
        """
        Check if subscription should be renewed.
        
        Args:
            expiration_datetime: ISO format expiration datetime
        
        Returns:
            True if subscription should be renewed (< 12 hours remaining)
        """
        try:
            expiration = datetime.fromisoformat(expiration_datetime.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            time_remaining = expiration - now
            
            return time_remaining < timedelta(hours=self.RENEWAL_THRESHOLD_HOURS)
            
        except Exception as e:
            logger.warning(f"Failed to parse expiration datetime: {e}")
            return True  # Renew if we can't parse (safe default)
    
    # Google Calendar Webhook Methods (Phase 5)
    
    async def create_google_subscription(
        self,
        integration: CalendarIntegration,
        access_token: str,
    ) -> dict:
        """
        Create Google Calendar push notification channel.
        
        Google Calendar uses "watch" API instead of subscriptions.
        
        Args:
            integration: Calendar integration
            access_token: Valid access token for Google Calendar API
        
        Returns:
            dict with channel details (id, resourceId, expiration)
        
        Note:
            This is a placeholder for Phase 5.
        """
        # TODO: Implement in Phase 5
        logger.info(f"Google Calendar webhook subscription not yet implemented (Phase 5)")
        raise NotImplementedError("Google Calendar webhooks will be implemented in Phase 5")
    
    async def stop_google_channel(
        self,
        channel_id: str,
        resource_id: str,
        access_token: str,
    ) -> None:
        """
        Stop Google Calendar push notification channel.
        
        Args:
            channel_id: Channel ID to stop
            resource_id: Resource ID from channel creation
            access_token: Valid access token for Google Calendar API
        
        Note:
            This is a placeholder for Phase 5.
        """
        # TODO: Implement in Phase 5
        logger.info(f"Google Calendar channel stop not yet implemented (Phase 5)")
        raise NotImplementedError("Google Calendar webhooks will be implemented in Phase 5")

