"""Custom exceptions for integration worker."""


class IntegrationWorkerError(Exception):
    """Base exception for integration worker errors."""
    pass


class SyncError(IntegrationWorkerError):
    """Error during calendar sync operation."""
    pass


class TokenRefreshError(IntegrationWorkerError):
    """Error refreshing OAuth token."""
    pass


class WebhookError(IntegrationWorkerError):
    """Error processing webhook notification."""
    pass


class ConfigurationError(IntegrationWorkerError):
    """Error in service configuration."""
    pass


class ExternalAPIError(IntegrationWorkerError):
    """Error calling external API (Microsoft Graph, Google Calendar, etc.)."""
    pass

