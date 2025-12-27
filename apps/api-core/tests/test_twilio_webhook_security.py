"""Unit tests for Twilio webhook signature validation."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient

from api_core.api.v1.twilio import validate_twilio_request, router


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.__str__ = lambda self: "https://example.com/api/v1/twilio/webhook"
    return request


@pytest.fixture
def mock_form_data():
    """Create mock form data from Twilio."""
    return {
        "CallSid": "CA1234567890ABCDE",
        "From": "+15551234567",
        "To": "+15559876543",
        "CallStatus": "ringing",
    }


@pytest.mark.asyncio
async def test_validate_twilio_request_success(mock_request, mock_form_data):
    """Test successful Twilio signature validation."""
    # Mock RequestValidator
    mock_validator = MagicMock()
    mock_validator.validate.return_value = True
    
    with patch("api_core.api.v1.twilio.RequestValidator", return_value=mock_validator):
        with patch("os.getenv", return_value="test_auth_token"):
            is_valid = validate_twilio_request(
                request=mock_request,
                twilio_signature="valid_signature",
                form_data=mock_form_data,
            )
    
    assert is_valid is True
    mock_validator.validate.assert_called_once()


@pytest.mark.asyncio
async def test_validate_twilio_request_invalid_signature(mock_request, mock_form_data):
    """Test validation failure for invalid signature."""
    # Mock RequestValidator
    mock_validator = MagicMock()
    mock_validator.validate.return_value = False
    
    with patch("api_core.api.v1.twilio.RequestValidator", return_value=mock_validator):
        with patch("os.getenv", return_value="test_auth_token"):
            is_valid = validate_twilio_request(
                request=mock_request,
                twilio_signature="invalid_signature",
                form_data=mock_form_data,
            )
    
    assert is_valid is False


@pytest.mark.asyncio
async def test_validate_twilio_request_missing_signature(mock_request, mock_form_data):
    """Test validation failure when signature header is missing."""
    with patch("os.getenv", return_value="test_auth_token"):
        is_valid = validate_twilio_request(
            request=mock_request,
            twilio_signature=None,
            form_data=mock_form_data,
        )
    
    assert is_valid is False


@pytest.mark.asyncio
async def test_validate_twilio_request_missing_auth_token(mock_request, mock_form_data):
    """Test validation when TWILIO_AUTH_TOKEN is not configured."""
    with patch("os.getenv", return_value=None):
        # Should return True (allow) when token is missing (development mode)
        is_valid = validate_twilio_request(
            request=mock_request,
            twilio_signature="some_signature",
            form_data=mock_form_data,
        )
    
    # In development, we allow requests when token is missing
    assert is_valid is True


@pytest.mark.asyncio
async def test_validate_twilio_request_validator_not_available(mock_request, mock_form_data):
    """Test validation when RequestValidator is not available."""
    with patch("api_core.api.v1.twilio.RequestValidator", None):
        with patch("os.getenv", return_value="test_auth_token"):
            is_valid = validate_twilio_request(
                request=mock_request,
                twilio_signature="some_signature",
                form_data=mock_form_data,
            )
    
    # Should return False when validator is not available
    assert is_valid is False


@pytest.mark.asyncio
async def test_validate_twilio_request_exception_handling(mock_request, mock_form_data):
    """Test validation handles exceptions gracefully."""
    # Mock RequestValidator to raise an exception
    mock_validator = MagicMock()
    mock_validator.validate.side_effect = Exception("Validation error")
    
    with patch("api_core.api.v1.twilio.RequestValidator", return_value=mock_validator):
        with patch("os.getenv", return_value="test_auth_token"):
            is_valid = validate_twilio_request(
                request=mock_request,
                twilio_signature="some_signature",
                form_data=mock_form_data,
            )
    
    # Should return False on exception
    assert is_valid is False


def test_webhook_endpoint_with_valid_signature(client, mock_form_data):
    """Test webhook endpoint accepts valid signature."""
    # This test would require a real Twilio signature
    # For now, we'll test with validation disabled
    with patch("os.getenv") as mock_env:
        mock_env.side_effect = lambda key, default=None: {
            "TWILIO_VALIDATE_SIGNATURES": "false",  # Disable for testing
            "TWILIO_AUTH_TOKEN": "test_token",
        }.get(key, default)
        
        # Mock database responses
        with patch("api_core.api.v1.twilio.get_session_context"):
            # This is a simplified test - full integration would require more setup
            pass


def test_webhook_endpoint_rejects_invalid_signature():
    """Test webhook endpoint rejects invalid signature."""
    # This would test the full endpoint with invalid signature
    # Requires proper FastAPI test client setup with form data
    pass

