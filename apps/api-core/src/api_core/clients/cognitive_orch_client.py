"""Client for communicating with the Cognitive Orchestrator service."""

from typing import Any, Dict

from py_common.clients import InternalAPIClient

from api_core.config import get_settings


class CognitiveOrchClient:
    """
    Client for making requests to the Cognitive Orchestrator service.
    
    Handles authentication via internal API key and provides methods
    for interacting with the orchestrator's chat endpoint.
    """
    
    def __init__(self):
        """Initialize the Cognitive Orchestrator client."""
        settings = get_settings()
        self._client = InternalAPIClient(
            base_url=settings.cognitive_orch.url,
            api_key=settings.cognitive_orch.api_key,
            timeout=float(settings.cognitive_orch.timeout),
        )
    
    async def chat(
        self,
        message: str,
        user_id: str,
        firm_id: str | None = None,
        conversation_id: str | None = None,
        tools_enabled: bool = False,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Send a chat message to the Cognitive Orchestrator.
        
        Args:
            message: The user's message/query
            user_id: User ID
            firm_id: Optional firm ID
            conversation_id: Optional conversation ID (for continuing conversations)
            tools_enabled: Whether to enable tool calling
            temperature: Sampling temperature (0.0-2.0)
            
        Returns:
            Response dictionary with conversation_id, response, tool_results, and iterations
            
        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        payload: Dict[str, Any] = {
            "message": message,
            "user_id": user_id,
            "tools_enabled": tools_enabled,
            "temperature": temperature,
        }
        
        if firm_id:
            payload["firm_id"] = firm_id
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        return await self._client.post("/api/v1/orchestrator/chat", json=payload)

