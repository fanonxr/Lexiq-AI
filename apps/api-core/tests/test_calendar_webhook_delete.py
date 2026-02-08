"""Unit tests for CalendarIntegrationService.delete_outlook_webhook_subscription."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import CalendarIntegration
from api_core.services.calendar_integration_service import CalendarIntegrationService


def _make_integration(
    integration_type: str = "outlook",
    webhook_subscription_id: str | None = "sub-123",
    integration_id: str = "int-1",
) -> CalendarIntegration:
    """Build a CalendarIntegration-like object for testing."""
    integration = MagicMock(spec=CalendarIntegration)
    integration.integration_type = integration_type
    integration.webhook_subscription_id = webhook_subscription_id
    integration.id = integration_id
    integration.access_token = "token"
    integration.token_expires_at = None
    return integration


@pytest.mark.asyncio
async def test_delete_outlook_webhook_no_op_for_google(session: AsyncSession):
    """Google integration is skipped (no Graph webhook)."""
    service = CalendarIntegrationService(session)
    integration = _make_integration(integration_type="google")
    with patch.object(
        service, "get_valid_access_token", new_callable=AsyncMock
    ) as mock_token:
        await service.delete_outlook_webhook_subscription(integration)
    mock_token.assert_not_called()


@pytest.mark.asyncio
async def test_delete_outlook_webhook_no_op_without_subscription_id(session: AsyncSession):
    """Outlook integration without webhook_subscription_id is skipped."""
    service = CalendarIntegrationService(session)
    integration = _make_integration(webhook_subscription_id=None)
    with patch.object(
        service, "get_valid_access_token", new_callable=AsyncMock
    ) as mock_token:
        await service.delete_outlook_webhook_subscription(integration)
    mock_token.assert_not_called()


@pytest.mark.asyncio
async def test_delete_outlook_webhook_calls_graph_delete(session: AsyncSession):
    """Outlook with webhook id calls Graph DELETE and accepts 204."""
    service = CalendarIntegrationService(session)
    integration = _make_integration(
        integration_type="outlook",
        webhook_subscription_id="graph-sub-456",
        integration_id="int-2",
    )
    with patch.object(
        service, "get_valid_access_token", new_callable=AsyncMock
    ) as mock_token:
        mock_token.return_value = "access-token"
        with patch("api_core.services.calendar_integration_service.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.AsyncClient.return_value = mock_client

            await service.delete_outlook_webhook_subscription(integration)

    mock_token.assert_called_once_with(integration)
    mock_client.delete.assert_awaited_once()
    call_args = mock_client.delete.call_args
    assert call_args[0][0] == "https://graph.microsoft.com/v1.0/subscriptions/graph-sub-456"
    assert call_args[1]["headers"]["Authorization"] == "Bearer access-token"


@pytest.mark.asyncio
async def test_delete_outlook_webhook_accepts_404(session: AsyncSession):
    """Outlook webhook delete treats 404 as success (subscription already gone)."""
    service = CalendarIntegrationService(session)
    integration = _make_integration(webhook_subscription_id="gone-sub")
    with patch.object(
        service, "get_valid_access_token", new_callable=AsyncMock
    ) as mock_token:
        mock_token.return_value = "token"
        with patch("api_core.services.calendar_integration_service.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.AsyncClient.return_value = mock_client

            await service.delete_outlook_webhook_subscription(integration)

    mock_client.delete.assert_awaited_once()
