"""Unit tests for get_user_or_internal_auth dependency."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

# Import the function - we'll call it directly bypassing FastAPI dependency injection
from api_core.auth.dependencies import get_user_or_internal_auth
from api_core.auth.token_validator import TokenValidationResult
from api_core.config import Settings


# Helper function to call get_user_or_internal_auth without FastAPI dependency injection
async def call_get_user_or_internal_auth(token=None, x_internal_api_key=None):
    """Helper to call get_user_or_internal_auth directly, bypassing FastAPI Depends/Header."""
    # When calling directly, the Depends() and Header() defaults are ignored
    # and we pass the values directly as function parameters
    return await get_user_or_internal_auth(token=token, x_internal_api_key=x_internal_api_key)


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = MagicMock(spec=Settings)
    settings.internal_api_key_enabled = False
    settings.internal_api_key = None
    return settings


@pytest.fixture
def mock_token_validation_result():
    """Create a mock token validation result."""
    result = MagicMock(spec=TokenValidationResult)
    result.user_id = "user-123"
    result.email = "user@example.com"
    result.token_type = "azure_ad_b2c"
    result.user_info = None
    return result


class TestGetUserOrInternalAuth:
    """Test suite for get_user_or_internal_auth dependency."""
    
    @pytest.mark.asyncio
    async def test_internal_api_key_when_enabled_and_valid(self, mock_settings):
        """Test that valid internal API key returns None (skip user auth)."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.config.get_settings", return_value=mock_settings):
            result = await call_get_user_or_internal_auth(
                token=None,
                x_internal_api_key="valid-key-123"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_internal_api_key_when_enabled_but_invalid(self, mock_settings):
        """Test that invalid internal API key falls through to user auth."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        mock_validator = AsyncMock()
        mock_result = MagicMock(spec=TokenValidationResult)
        mock_result.user_id = "user-123"
        mock_validator.validate_token.return_value = mock_result
        
        with patch("api_core.config.get_settings", return_value=mock_settings), \
             patch("api_core.auth.dependencies.get_token_validator", return_value=mock_validator):
            
            # Should try user auth since internal key is invalid
            with pytest.raises(HTTPException) as exc_info:
                await call_get_user_or_internal_auth(
                    token=None,
                    x_internal_api_key="wrong-key"
                )
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_internal_api_key_when_disabled(self, mock_settings):
        """Test that when disabled, internal API key is ignored."""
        mock_settings.internal_api_key_enabled = False
        
        mock_validator = AsyncMock()
        mock_result = MagicMock(spec=TokenValidationResult)
        mock_result.user_id = "user-123"
        mock_result.token_type = "access"  # Not azure_ad_b2c to avoid user sync
        mock_result.user_info = None
        mock_validator.validate_token.return_value = mock_result
        
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            yield MagicMock()
        
        with patch("api_core.config.get_settings", return_value=mock_settings), \
             patch("api_core.auth.dependencies.get_token_validator", return_value=mock_validator), \
             patch("api_core.auth.dependencies.get_session_context", side_effect=mock_session_context), \
             patch("api_core.auth.dependencies.get_user_service", return_value=MagicMock()):
            
            result = await call_get_user_or_internal_auth(
                token="valid-user-token",
                x_internal_api_key="any-key"
            )
            
            assert result is not None
            assert result.user_id == "user-123"
    
    @pytest.mark.asyncio
    async def test_user_token_when_no_internal_key(self, mock_settings, mock_token_validation_result):
        """Test that user token works when no internal key provided."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        mock_validator = AsyncMock()
        mock_validator.validate_token.return_value = mock_token_validation_result
        
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_session_context():
            yield MagicMock()
        
        with patch("api_core.config.get_settings", return_value=mock_settings), \
             patch("api_core.auth.dependencies.get_token_validator", return_value=mock_validator), \
             patch("api_core.auth.dependencies.get_session_context", side_effect=mock_session_context), \
             patch("api_core.auth.dependencies.get_user_service", return_value=MagicMock()):
            
            result = await call_get_user_or_internal_auth(
                token="valid-user-token",
                x_internal_api_key=None
            )
            
            assert result is not None
            assert result.user_id == "user-123"
    
    @pytest.mark.asyncio
    async def test_no_auth_provided_raises(self, mock_settings):
        """Test that when neither token nor internal key provided, raises 401."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        with patch("api_core.config.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await call_get_user_or_internal_auth(
                    token=None,
                    x_internal_api_key=None
                )
            
            assert exc_info.value.status_code == 401
            assert "Not authenticated" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_invalid_user_token_raises(self, mock_settings):
        """Test that invalid user token raises 401."""
        mock_settings.internal_api_key_enabled = True
        mock_settings.internal_api_key = "valid-key-123"
        
        mock_validator = AsyncMock()
        from api_core.exceptions import AuthenticationError
        mock_validator.validate_token.side_effect = AuthenticationError("Invalid token")
        
        with patch("api_core.config.get_settings", return_value=mock_settings), \
             patch("api_core.auth.dependencies.get_token_validator", return_value=mock_validator):
            
            with pytest.raises(HTTPException) as exc_info:
                await call_get_user_or_internal_auth(
                    token="invalid-token",
                    x_internal_api_key=None
                )
            
            assert exc_info.value.status_code == 401

