"""Unit tests for InternalAPIClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from typing import Dict, Any

from py_common.clients.internal_api_client import InternalAPIClient


@pytest.fixture
def base_url():
    """Base URL for testing."""
    return "http://test-api:8000"


@pytest.fixture
def api_key():
    """API key for testing."""
    return "test-api-key-12345"


class TestInternalAPIClient:
    """Test suite for InternalAPIClient."""
    
    def test_init_with_api_key(self, base_url, api_key):
        """Test client initialization with API key."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        assert client.base_url == base_url
        assert client.timeout == 30.0
        assert "X-Internal-API-Key" in client._headers
        assert client._headers["X-Internal-API-Key"] == api_key
    
    def test_init_without_api_key(self, base_url):
        """Test client initialization without API key."""
        client = InternalAPIClient(base_url=base_url)
        
        assert client.base_url == base_url
        assert client.timeout == 30.0
        assert "X-Internal-API-Key" not in client._headers
    
    def test_init_with_custom_timeout(self, base_url):
        """Test client initialization with custom timeout."""
        client = InternalAPIClient(base_url=base_url, timeout=60.0)
        
        assert client.timeout == 60.0
    
    def test_init_with_default_headers(self, base_url, api_key):
        """Test client initialization with default headers."""
        default_headers = {"X-Custom-Header": "custom-value"}
        client = InternalAPIClient(
            base_url=base_url,
            api_key=api_key,
            default_headers=default_headers
        )
        
        assert client._headers["X-Custom-Header"] == "custom-value"
        assert client._headers["X-Internal-API-Key"] == api_key
    
    def test_build_url(self, base_url):
        """Test URL building."""
        client = InternalAPIClient(base_url=base_url)
        
        # Path with leading slash
        url = client._build_url("/api/v1/test")
        assert url == f"{base_url}/api/v1/test"
        
        # Path without leading slash
        url = client._build_url("api/v1/test")
        assert url == f"{base_url}/api/v1/test"
        
        # Base URL with trailing slash
        client_with_slash = InternalAPIClient(base_url=f"{base_url}/")
        url = client_with_slash._build_url("/api/v1/test")
        assert url == f"{base_url}/api/v1/test"
    
    def test_get_headers(self, base_url, api_key):
        """Test header merging."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        # Get headers without additional
        headers = client._get_headers()
        assert headers["X-Internal-API-Key"] == api_key
        
        # Get headers with additional
        additional = {"X-Custom-Header": "custom"}
        headers = client._get_headers(additional_headers=additional)
        assert headers["X-Internal-API-Key"] == api_key
        assert headers["X-Custom-Header"] == "custom"
        
        # Additional headers override defaults
        override = {"X-Internal-API-Key": "override"}
        headers = client._get_headers(additional_headers=override)
        assert headers["X-Internal-API-Key"] == "override"
    
    @pytest.mark.asyncio
    async def test_get_success(self, base_url, api_key):
        """Test successful GET request."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "data": "test"}
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            result = await client.get("/api/v1/test")
            
            assert result == {"status": "ok", "data": "test"}
            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["headers"]["X-Internal-API-Key"] == api_key
    
    @pytest.mark.asyncio
    async def test_post_success(self, base_url, api_key):
        """Test successful POST request."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "status": "created"}
        mock_response.status_code = 201
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            payload = {"name": "test", "value": 42}
            result = await client.post("/api/v1/test", json=payload)
            
            assert result == {"id": "123", "status": "created"}
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args[1]
            assert call_kwargs["json"] == payload
            assert call_kwargs["headers"]["X-Internal-API-Key"] == api_key
    
    @pytest.mark.asyncio
    async def test_put_success(self, base_url, api_key):
        """Test successful PUT request."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "status": "updated"}
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.put.return_value = mock_response
            
            payload = {"name": "updated"}
            result = await client.put("/api/v1/test/123", json=payload)
            
            assert result == {"id": "123", "status": "updated"}
            mock_client.put.assert_called_once()
            call_kwargs = mock_client.put.call_args[1]
            assert call_kwargs["json"] == payload
    
    @pytest.mark.asyncio
    async def test_delete_success(self, base_url, api_key):
        """Test successful DELETE request."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "deleted"}
        mock_response.status_code = 204
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.delete.return_value = mock_response
            
            result = await client.delete("/api/v1/test/123")
            
            assert result == {"status": "deleted"}
            mock_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_patch_success(self, base_url, api_key):
        """Test successful PATCH request."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "status": "patched"}
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.patch.return_value = mock_response
            
            payload = {"name": "patched"}
            result = await client.patch("/api/v1/test/123", json=payload)
            
            assert result == {"id": "123", "status": "patched"}
            mock_client.patch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_http_error_raises_exception(self, base_url, api_key):
        """Test that HTTP errors raise exceptions."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key)
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("/api/v1/test")
    
    @pytest.mark.asyncio
    async def test_timeout_configured(self, base_url, api_key):
        """Test that timeout is configured correctly."""
        client = InternalAPIClient(base_url=base_url, api_key=api_key, timeout=60.0)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "ok"}
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            await client.get("/api/v1/test")
            
            # Verify AsyncClient was created with correct timeout
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs["timeout"] == 60.0
    
    @pytest.mark.asyncio
    async def test_request_without_api_key(self, base_url):
        """Test request without API key doesn't include header."""
        client = InternalAPIClient(base_url=base_url)
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            await client.get("/api/v1/test")
            
            call_kwargs = mock_client.get.call_args[1]
            assert "X-Internal-API-Key" not in call_kwargs.get("headers", {})

