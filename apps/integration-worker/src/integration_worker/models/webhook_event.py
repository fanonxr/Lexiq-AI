"""Pydantic models for webhook events."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OutlookNotification(BaseModel):
    """Microsoft Graph webhook notification."""
    
    subscriptionId: str = Field(..., description="Subscription ID")
    subscriptionExpirationDateTime: str = Field(..., description="When subscription expires")
    changeType: str = Field(..., description="Type of change: created, updated, deleted")
    resource: str = Field(..., description="Resource URL (e.g., /me/events/123)")
    resourceData: Dict[str, Any] = Field(default_factory=dict, description="Resource data")
    clientState: str = Field(..., description="Client state (integration ID)")
    tenantId: Optional[str] = Field(default=None, description="Tenant ID")


class OutlookNotificationBatch(BaseModel):
    """Batch of Outlook notifications (Microsoft Graph sends as array)."""
    
    value: List[OutlookNotification] = Field(..., description="Array of notifications")


class GoogleNotification(BaseModel):
    """Google Calendar push notification (Phase 5)."""
    
    kind: str = Field(..., description="Notification kind")
    id: str = Field(..., description="Channel ID")
    resourceId: str = Field(..., description="Opaque resource ID")
    resourceUri: str = Field(..., description="Resource URI")
    channelId: str = Field(..., description="Channel ID")
    channelExpiration: Optional[str] = Field(default=None, description="Channel expiration")
    channelToken: Optional[str] = Field(default=None, description="Channel token (integration ID)")


class WebhookValidationRequest(BaseModel):
    """Webhook validation request (Microsoft Graph initial handshake)."""
    
    validationToken: Optional[str] = Field(default=None, description="Validation token from header")


class WebhookProcessingResult(BaseModel):
    """Result of webhook processing."""
    
    success: bool = Field(..., description="Whether processing was successful")
    integration_id: str = Field(..., description="Calendar integration ID")
    change_type: str = Field(..., description="Type of change processed")
    event_id: Optional[str] = Field(default=None, description="Event ID that was processed")
    error: Optional[str] = Field(default=None, description="Error message if failed")

