"""Unit tests for APICoreClient in document-ingestion."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from document_ingestion.clients.api_core_client import APICoreClient


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("CORE_API_URL", "http://api-core:8000")
    monkeypatch.setenv("CORE_API_API_KEY", "test-api-key")
    monkeypatch.setenv("CORE_API_TIMEOUT", "30")


class TestAPICoreClient:
    """Test suite for APICoreClient in document-ingestion."""
    
    def test_init(self, mock_env_vars):
        """Test client initialization."""
        client = APICoreClient()
        
        assert client._client.base_url == "http://api-core:8000"
        assert client._client.timeout == 30.0
    
    @pytest.mark.asyncio
    async def test_update_file_status(self, mock_env_vars):
        """Test update_file_status method."""
        from document_ingestion.models.message import IngestionStatus
        
        client = APICoreClient()
        
        with patch.object(client._client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {}
            
            # Should not raise
            await client.update_file_status(
                file_id="file-123",
                status=IngestionStatus.INDEXED,
                error_message=None
            )
            
            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert call_args[0][0] == "/api/v1/knowledge/files/file-123/status"
            assert call_args[1]["json"]["status"] == "indexed"
            assert "error_message" not in call_args[1]["json"]
    
    @pytest.mark.asyncio
    async def test_update_file_status_with_error(self, mock_env_vars):
        """Test update_file_status with error message."""
        from document_ingestion.models.message import IngestionStatus
        
        client = APICoreClient()
        
        with patch.object(client._client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {}
            
            await client.update_file_status(
                file_id="file-123",
                status=IngestionStatus.FAILED,
                error_message="Processing failed"
            )
            
            call_args = mock_put.call_args
            assert call_args[1]["json"]["error_message"] == "Processing failed"
            assert call_args[1]["json"]["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_update_qdrant_info(self, mock_env_vars):
        """Test update_qdrant_info method."""
        client = APICoreClient()
        
        with patch.object(client._client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.return_value = {}
            
            # Should not raise
            await client.update_qdrant_info(
                file_id="file-123",
                collection_name="firm-456",
                point_ids=["point-1", "point-2"]
            )
            
            mock_put.assert_called_once()
            call_args = mock_put.call_args
            assert call_args[0][0] == "/api/v1/knowledge/files/file-123/qdrant-info"
            assert call_args[1]["json"]["collection_name"] == "firm-456"
            assert call_args[1]["json"]["point_ids"] == ["point-1", "point-2"]
    
    @pytest.mark.asyncio
    async def test_http_error_raises_ingestion_exception(self, mock_env_vars):
        """Test that HTTP errors raise IngestionException."""
        from document_ingestion.models.message import IngestionStatus
        from document_ingestion.utils.errors import IngestionException
        
        client = APICoreClient()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        http_error = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(client._client, "put", new_callable=AsyncMock) as mock_put:
            mock_put.side_effect = http_error
            
            with pytest.raises(IngestionException) as exc_info:
                await client.update_file_status(
                    file_id="file-123",
                    status=IngestionStatus.INDEXED
                )
            
            assert exc_info.value.status_code == 404
            assert "File not found" in str(exc_info.value)

