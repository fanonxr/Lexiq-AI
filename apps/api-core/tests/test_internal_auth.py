"""Unit tests for internal API key authentication."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, Header
from fastapi.testclient import TestClient

from api_core.auth.internal_service import require_internal_api_key, check_internal_api_key, InternalAuthDep
from api_core.config import Settings


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock(spec=Settings)
    settings.internal_api_key_enabled = False
    settings.internal_api_key = None
    return settings


class TestRequireInternalAPIKey:
    """Test suite for require_internal_api_key dependency."""
    
    @pytest.mark.asyncio
    async def test_disabled_allows_request(self, mock_settings):
        """Test that when disabled, requests are allowed."""
        mock_settings.internal_api_key_enabled = False
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            # Should not raise
            await require_internal_api_key(x_internal_api_key=None)
            await require_internal_api_key(x_internal_api_key="any-key")
    
    @pytest.mark.asyncio
    async def test_enabled_with_valid_key(self, mock_settings):
        """Test that when enabled, valid key is accepted."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            # Should not raise
            await require_internal_api_key(x_internal_api_key="valid-key-123")
    
    @pytest.mark.asyncio
    async def test_enabled_with_invalid_key_raises(self, mock_settings):
        """Test that when enabled, invalid key raises 401."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await require_internal_api_key(x_internal_api_key="wrong-key")
            
            assert exc_info.value.status_code == 401
            assert "Invalid internal API key" in exc_info.value.detail
            assert "WWW-Authenticate" in exc_info.value.headers
    
    @pytest.mark.asyncio
    async def test_enabled_with_missing_key_raises(self, mock_settings):
        """Test that when enabled, missing key raises 401."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await require_internal_api_key(x_internal_api_key=None)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_enabled_but_key_not_set_raises_500(self, mock_settings):
        """Test that when enabled but key not configured, raises 500."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = None
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await require_internal_api_key(x_internal_api_key="any-key")
            
            assert exc_info.value.status_code == 500
            assert "misconfigured" in exc_info.value.detail.lower()


class TestCheckInternalAPIKey:
    """Test suite for check_internal_api_key function."""
    
    @pytest.mark.asyncio
    async def test_disabled_returns_false(self, mock_settings):
        """Test that when disabled, returns False."""
        mock_settings.internal_api_key_enabled = False
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key="any-key")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_enabled_with_valid_key_returns_true(self, mock_settings):
        """Test that when enabled with valid key, returns True."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key="valid-key-123")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_enabled_with_invalid_key_returns_false(self, mock_settings):
        """Test that when enabled with invalid key, returns False."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key="wrong-key")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_enabled_with_missing_key_returns_false(self, mock_settings):
        """Test that when enabled with missing key, returns False."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key=None)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_enabled_but_key_not_set_returns_false(self, mock_settings):
        """Test that when enabled but key not set, returns False."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = None
        
        with patch("api_core.auth.internal_service.settings", mock_settings):
            result = await check_internal_api_key(x_internal_api_key="any-key")
            assert result is False


class TestInternalAuthDep:
    """Test suite for InternalAuthDep dependency."""
    
    def test_is_dependency(self):
        """Test that InternalAuthDep is a FastAPI dependency."""
        from fastapi import Depends
        
        assert isinstance(InternalAuthDep, Depends)

