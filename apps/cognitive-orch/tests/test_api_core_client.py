"""Unit tests for APICoreClient in cognitive-orch."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from cognitive_orch.clients.api_core_client import APICoreClient
from cognitive_orch.config import Settings, IntegrationSettings


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock(spec=Settings)
    settings.integration = MagicMock(spec=IntegrationSettings)
    settings.integration.core_api_url = "http://api-core:8000"
    settings.integration.core_api_api_key = "test-api-key"
    settings.integration.core_api_timeout = 30
    return settings


class TestAPICoreClient:
    """Test suite for APICoreClient."""
    
    def test_init(self, mock_settings):
        """Test client initialization."""
        with patch("cognitive_orch.clients.api_core_client.settings", mock_settings):
            client = APICoreClient()
            
            assert client._client.base_url == "http://api-core:8000"
            assert client._client.timeout == 30.0
    
    @pytest.mark.asyncio
    async def test_check_availability(self, mock_settings):
        """Test check_availability method."""
        with patch("cognitive_orch.clients.api_core_client.settings", mock_settings):
            client = APICoreClient()
            
            mock_response = {
                "slots": [
                    {"start": "2024-01-01T10:00:00Z", "end": "2024-01-01T10:30:00Z"}
                ]
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                payload = {
                    "start_time": "2024-01-01T09:00:00Z",
                    "end_time": "2024-01-01T17:00:00Z"
                }
                result = await client.check_availability(payload)
                
                assert result == mock_response
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "/api/v1/appointments/availability"
                assert call_args[1]["json"] == payload
    
    @pytest.mark.asyncio
    async def test_book_appointment(self, mock_settings):
        """Test book_appointment method."""
        with patch("cognitive_orch.clients.api_core_client.settings", mock_settings):
            client = APICoreClient()
            
            mock_response = {
                "id": "apt-123",
                "status": "confirmed"
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                payload = {
                    "client_name": "John Doe",
                    "date_time": "2024-01-01T10:00:00Z"
                }
                result = await client.book_appointment(payload)
                
                assert result == mock_response
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "/api/v1/appointments"
                assert call_args[1]["json"] == payload
    
    @pytest.mark.asyncio
    async def test_create_lead(self, mock_settings):
        """Test create_lead method."""
        with patch("cognitive_orch.clients.api_core_client.settings", mock_settings):
            client = APICoreClient()
            
            mock_response = {
                "id": "lead-123",
                "status": "new"
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                payload = {
                    "name": "Jane Doe",
                    "email": "jane@example.com"
                }
                result = await client.create_lead(payload)
                
                assert result == mock_response
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "/api/v1/leads"
                assert call_args[1]["json"] == payload
    
    @pytest.mark.asyncio
    async def test_send_notification(self, mock_settings):
        """Test send_notification method."""
        with patch("cognitive_orch.clients.api_core_client.settings", mock_settings):
            client = APICoreClient()
            
            mock_response = {
                "id": "notif-123",
                "status": "sent"
            }
            
            with patch.object(client._client, "post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                
                payload = {
                    "message": "Test notification",
                    "recipient": "user@example.com"
                }
                result = await client.send_notification(payload)
                
                assert result == mock_response
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == "/api/v1/notifications"
                assert call_args[1]["json"] == payload
    
    @pytest.mark.asyncio
    async def test_http_error_propagates(self, mock_settings):
        """Test that HTTP errors are propagated."""
        with patch("cognitive_orch.clients.api_core_client.settings", mock_settings):
            client = APICoreClient()
            
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
                    await client.check_availability({})

