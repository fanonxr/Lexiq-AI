"""Tests for custom exceptions."""

import pytest

from integration_worker.utils.errors import (
    IntegrationWorkerError,
    SyncError,
    TokenRefreshError,
    WebhookError,
    ConfigurationError,
    ExternalAPIError,
)


class TestCustomExceptions:
    """Test suite for custom exceptions."""
    
    def test_base_exception(self):
        """Test base IntegrationWorkerError."""
        error = IntegrationWorkerError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_sync_error(self):
        """Test SyncError exception."""
        error = SyncError("Sync failed")
        assert str(error) == "Sync failed"
        assert isinstance(error, IntegrationWorkerError)
    
    def test_token_refresh_error(self):
        """Test TokenRefreshError exception."""
        error = TokenRefreshError("Token refresh failed")
        assert str(error) == "Token refresh failed"
        assert isinstance(error, IntegrationWorkerError)
    
    def test_webhook_error(self):
        """Test WebhookError exception."""
        error = WebhookError("Webhook processing failed")
        assert str(error) == "Webhook processing failed"
        assert isinstance(error, IntegrationWorkerError)
    
    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert isinstance(error, IntegrationWorkerError)
    
    def test_external_api_error(self):
        """Test ExternalAPIError exception."""
        error = ExternalAPIError("API call failed")
        assert str(error) == "API call failed"
        assert isinstance(error, IntegrationWorkerError)
    
    def test_exception_inheritance(self):
        """Test that all custom exceptions inherit from base."""
        assert issubclass(SyncError, IntegrationWorkerError)
        assert issubclass(TokenRefreshError, IntegrationWorkerError)
        assert issubclass(WebhookError, IntegrationWorkerError)
        assert issubclass(ConfigurationError, IntegrationWorkerError)
        assert issubclass(ExternalAPIError, IntegrationWorkerError)

