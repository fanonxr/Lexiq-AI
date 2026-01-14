"""Unit tests for internal API key authentication in cognitive-orch."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from cognitive_orch.auth.internal_service import require_internal_api_key, check_internal_api_key, InternalAuthDep
from cognitive_orch.config import Settings


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock(spec=Settings)
    settings.internal_api_key_enabled = False
    settings.internal_api_key = None
    return settings


class TestRequireInternalAPIKey:
    """Test suite for require_internal_api_key dependency in cognitive-orch."""
    
    @pytest.mark.asyncio
    async def test_disabled_allows_request(self, mock_settings):
        """Test that when disabled, requests are allowed."""
        mock_settings.internal_api_key_enabled = False
        
        with patch("cognitive_orch.auth.internal_service.settings", mock_settings):
            await require_internal_api_key(x_internal_api_key=None)
            await require_internal_api_key(x_internal_api_key="any-key")
    
    @pytest.mark.asyncio
    async def test_enabled_with_valid_key(self, mock_settings):
        """Test that when enabled, valid key is accepted."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("cognitive_orch.auth.internal_service.settings", mock_settings):
            await require_internal_api_key(x_internal_api_key="valid-key-123")
    
    @pytest.mark.asyncio
    async def test_enabled_with_invalid_key_raises(self, mock_settings):
        """Test that when enabled, invalid key raises 401."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("cognitive_orch.auth.internal_service.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await require_internal_api_key(x_internal_api_key="wrong-key")
            
            assert exc_info.value.status_code == 401
            assert "Invalid internal API key" in exc_info.value.detail


class TestCheckInternalAPIKey:
    """Test suite for check_internal_api_key function in cognitive-orch."""
    
    @pytest.mark.asyncio
    async def test_disabled_returns_false(self, mock_settings):
        """Test that when disabled, returns False."""
        mock_settings.internal_api_key_enabled = False
        
        with patch("cognitive_orch.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key="any-key")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_enabled_with_valid_key_returns_true(self, mock_settings):
        """Test that when enabled with valid key, returns True."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("cognitive_orch.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key="valid-key-123")
            assert result is True


class TestInternalAuthDep:
    """Test suite for InternalAuthDep dependency in cognitive-orch."""
    
    def test_is_dependency(self):
        """Test that InternalAuthDep is a FastAPI dependency."""
        from fastapi import Depends
        
        # Check that it was created with Depends by checking the type name
        assert type(InternalAuthDep).__name__ == "Depends"
        # Check that it has the dependency property
        assert hasattr(InternalAuthDep, "dependency")
        # Verify the dependency is the require_internal_api_key function
        from cognitive_orch.auth.internal_service import require_internal_api_key
        assert InternalAuthDep.dependency == require_internal_api_key

