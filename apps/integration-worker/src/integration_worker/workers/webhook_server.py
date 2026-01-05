"""FastAPI server for webhook endpoints.

This server receives webhook notifications from external services:
- Microsoft Graph (Outlook calendar events)
- Google Calendar (Phase 5)
- Clio CRM (Phase 6)
"""

import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from integration_worker.config import get_settings
from integration_worker.models.webhook_event import (
    OutlookNotification,
    OutlookNotificationBatch,
    WebhookProcessingResult,
)
from integration_worker.tasks.webhook_processing import process_outlook_notification
from integration_worker.utils.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Integration Worker Webhook Server",
    description="Receives webhook notifications from calendar and CRM integrations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware (if needed for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    
    Returns service health status.
    """
    return {
        "status": "healthy",
        "service": "integration-worker-webhook-server",
        "version": "1.0.0"
    }


@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Checks if service is ready to receive webhooks.
    """
    # TODO: Add checks for Redis connection, Celery worker availability
    return {
        "status": "ready",
        "service": "integration-worker-webhook-server",
    }


@app.post(
    "/webhooks/outlook/notifications",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
    summary="Receive Outlook calendar webhook notifications",
    description="Endpoint for Microsoft Graph webhook notifications about calendar events",
)
async def handle_outlook_notifications(
    request: Request,
    validationtoken: Optional[str] = Header(None, alias="validationtoken"),
):
    """
    Handle Outlook calendar webhook notifications from Microsoft Graph.
    
    Microsoft Graph Webhook Flow:
    
    1. **Validation Handshake** (on subscription creation):
       - Microsoft sends GET/POST with `validationtoken` header
       - We must respond with the token as plain text
       - This proves we control the endpoint
    
    2. **Event Notifications** (when events change):
       - Microsoft sends POST with JSON body
       - Body contains array of notifications
       - We queue tasks and respond 202 Accepted quickly
    
    Args:
        request: FastAPI request object
        validationtoken: Validation token from Microsoft Graph (initial handshake)
    
    Returns:
        202 Accepted with processing status
    """
    # Handle validation handshake (first time setup)
    if validationtoken:
        logger.info(
            "Received Microsoft Graph webhook validation request, "
            f"returning validation token (length: {len(validationtoken)})"
        )
        # Must return the validation token as plain text
        return Response(
            content=validationtoken,
            media_type="text/plain",
            status_code=200,
        )
    
    # Process notification
    try:
        body = await request.json()
        logger.debug(f"Received webhook notification: {body}")
        
        # Parse notification batch
        try:
            notification_batch = OutlookNotificationBatch(**body)
        except Exception as e:
            logger.error(f"Failed to parse notification batch: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notification format: {str(e)}"
            )
        
        # Process each notification
        queued_tasks = []
        for notification in notification_batch.value:
            try:
                # Verify clientState matches integration_id format
                integration_id = notification.clientState
                if not integration_id:
                    logger.warning("Notification missing clientState, skipping")
                    continue
                
                # Extract resource data
                resource_data = notification.resourceData or {}
                
                # Queue async task for processing
                task = process_outlook_notification.delay(
                    integration_id=integration_id,
                    change_type=notification.changeType,
                    resource=notification.resource,
                    resource_data=resource_data,
                )
                
                queued_tasks.append(task.id)
                
                logger.info(
                    f"Queued Outlook notification processing task {task.id}: "
                    f"{notification.changeType} for integration {integration_id}"
                )
                
            except Exception as e:
                # Log error but don't fail the entire batch
                logger.error(
                    f"Error queuing notification task: {e}",
                    exc_info=True,
                )
        
        # Return 202 Accepted quickly (< 1 second)
        # Microsoft Graph requires response within 3 seconds
        return {
            "status": "accepted",
            "notifications_received": len(notification_batch.value),
            "tasks_queued": len(queued_tasks),
            "task_ids": queued_tasks,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing Outlook webhook notifications: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook notifications"
        )


@app.post(
    "/webhooks/google/notifications",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Google Calendar webhook notifications (Phase 5)",
    description="Endpoint for Google Calendar push notifications",
)
async def handle_google_notifications(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None, alias="X-Goog-Channel-ID"),
    x_goog_resource_state: Optional[str] = Header(None, alias="X-Goog-Resource-State"),
):
    """
    Handle Google Calendar push notifications.
    
    Note: This is a placeholder for Phase 5.
    
    Args:
        request: FastAPI request object
        x_goog_channel_id: Channel ID from Google
        x_goog_resource_state: Resource state (sync, exists, not_exists)
    
    Returns:
        202 Accepted
    """
    logger.info(
        f"Received Google Calendar notification (Phase 5 - not yet implemented): "
        f"channel={x_goog_channel_id}, state={x_goog_resource_state}"
    )
    
    # For now, just acknowledge
    return {
        "status": "accepted",
        "message": "Google Calendar webhooks will be implemented in Phase 5"
    }


@app.get("/webhooks/subscriptions", status_code=status.HTTP_200_OK)
async def list_webhook_subscriptions():
    """
    List all active webhook subscriptions (for debugging/monitoring).
    
    Returns:
        List of active subscriptions
    """
    # TODO: Query database for integrations with active webhook subscriptions
    return {
        "subscriptions": [],
        "message": "Subscription listing not yet implemented"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(
        f"Starting Integration Worker Webhook Server "
        f"(environment: {settings.environment})"
    )
    logger.info(f"Webhook base URL: {settings.webhook_base_url}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down Integration Worker Webhook Server")


# Root endpoint
@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint with service information."""
    return {
        "service": "integration-worker-webhook-server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "docs": "/docs",
            "outlook_webhooks": "/webhooks/outlook/notifications",
            "google_webhooks": "/webhooks/google/notifications (Phase 5)",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level=settings.log_level.lower(),
    )

