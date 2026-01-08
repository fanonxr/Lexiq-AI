"""Unit tests for CognitiveOrchClient."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from api_core.clients.cognitive_orch_client import CognitiveOrchClient
from api_core.config import Settings, CognitiveOrchSettings


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock(spec=Settings)
    settings.cognitive_orch = MagicMock(spec=CognitiveOrchSettings)
    settings.cognitive_orch.url = "http://cognitive-orch:8001"
    settings.cognitive_orch.api_key = "test-api-key"
    settings.cognitive_orch.timeout = 30
    return settings


class TestCognitiveOrchClient:
    """Test suite for CognitiveOrchClient."""
    
    def test_init(self, mock_settings):
        """Test client initialization."""
        with patch("api_core.clients.cognitive_orch_client.get_settings", return_value=mock_settings):
            client = CognitiveOrchClient()
            
            assert client._client.base_url == "http://cognitive-orch:8001"
            assert client._client.timeout == 30.0
    
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_settings):
        """Test successful chat request."""
        with patch("api_core.clients.cognitive_orch_client.get_settings", return_value=mock_settings):
            client = CognitiveOrchClient()
            
            mock_response = {
                "conversation_id": "conv-123",
                "response": "Hello, how can I help?",
                "tool_results": [],
                "iterations": 1
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                result = await client.chat(
                    message="Hello",
                    user_id="user-123",
                    firm_id="firm-456",
                    tools_enabled=False,
                    temperature=0.7
                )
                
                assert result == mock_response
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "/api/v1/orchestrator/chat"
                assert call_args[1]["json"]["message"] == "Hello"
                assert call_args[1]["json"]["user_id"] == "user-123"
                assert call_args[1]["json"]["firm_id"] == "firm-456"
                assert call_args[1]["json"]["tools_enabled"] is False
                assert call_args[1]["json"]["temperature"] == 0.7
    
    @pytest.mark.asyncio
    async def test_chat_without_firm_id(self, mock_settings):
        """Test chat request without firm_id."""
        with patch("api_core.clients.cognitive_orch_client.get_settings", return_value=mock_settings):
            client = CognitiveOrchClient()
            
            mock_response = {
                "conversation_id": "conv-123",
                "response": "Hello",
                "tool_results": [],
                "iterations": 1
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                result = await client.chat(
                    message="Hello",
                    user_id="user-123",
                    firm_id=None,
                    tools_enabled=True,
                    temperature=0.5
                )
                
                assert result == mock_response
                call_args = mock_post.call_args
                json_payload = call_args[1]["json"]
                assert "firm_id" not in json_payload
    
    @pytest.mark.asyncio
    async def test_chat_with_conversation_id(self, mock_settings):
        """Test chat request with conversation_id."""
        with patch("api_core.clients.cognitive_orch_client.get_settings", return_value=mock_settings):
            client = CognitiveOrchClient()
            
            mock_response = {
                "conversation_id": "conv-123",
                "response": "Hello",
                "tool_results": [],
                "iterations": 1
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                result = await client.chat(
                    message="Hello",
                    user_id="user-123",
                    conversation_id="conv-123"
                )
                
                assert result == mock_response
                call_args = mock_post.call_args
                json_payload = call_args[1]["json"]
                assert json_payload["conversation_id"] == "conv-123"
    
    @pytest.mark.asyncio
    async def test_chat_http_error(self, mock_settings):
        """Test chat request with HTTP error."""
        with patch("api_core.clients.cognitive_orch_client.get_settings", return_value=mock_settings):
            client = CognitiveOrchClient()
            
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            http_error = httpx.HTTPStatusError(
                "Internal Server Error",
                request=MagicMock(),
                response=mock_response
            )
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.side_effect = http_error
                
                with pytest.raises(httpx.HTTPStatusError):
                    await client.chat(
                        message="Hello",
                        user_id="user-123"
                    )
    
    @pytest.mark.asyncio
    async def test_chat_timeout(self, mock_settings):
        """Test chat request with timeout."""
        with patch("api_core.clients.cognitive_orch_client.get_settings", return_value=mock_settings):
            client = CognitiveOrchClient()
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.side_effect = httpx.TimeoutException("Request timed out")
                
                with pytest.raises(httpx.TimeoutException):
                    await client.chat(
                        message="Hello",
                        user_id="user-123"
                    )

