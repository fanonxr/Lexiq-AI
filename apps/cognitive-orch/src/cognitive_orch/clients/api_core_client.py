"""API Core client for Cognitive Orchestrator service-to-service communication."""

from typing import Any, Dict, Optional

from cognitive_orch.config import get_settings
from py_common.clients import InternalAPIClient

settings = get_settings()


class APICoreClient:
    """
    HTTP client for communicating with API Core service.
    
    Wraps InternalAPIClient with cognitive-orch specific configuration.
    """

    def __init__(self):
        """Initialize API Core client."""
        self._client = InternalAPIClient(
            base_url=settings.integration.core_api_url,
            api_key=settings.integration.core_api_api_key,
            timeout=float(settings.integration.core_api_timeout),
        )

    async def check_availability(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check appointment availability.
        
        Args:
            payload: Availability request payload
            
        Returns:
            Availability response as dictionary
        """
        return await self._client.post("/api/v1/appointments/availability", json=payload)

    async def book_appointment(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Book an appointment.
        
        Args:
            payload: Appointment booking payload
            
        Returns:
            Appointment response as dictionary
        """
        return await self._client.post("/api/v1/appointments", json=payload)

    async def create_lead(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a lead.
        
        Args:
            payload: Lead creation payload
            
        Returns:
            Lead response as dictionary
        """
        return await self._client.post("/api/v1/leads", json=payload)

    async def send_notification(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send a notification.
        
        Args:
            payload: Notification payload
            
        Returns:
            Notification response as dictionary
        """
        return await self._client.post("/api/v1/notifications", json=payload)

