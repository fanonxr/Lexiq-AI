"""Tests for OutlookService."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from integration_worker.services.outlook_service import OutlookService
from integration_worker.models.sync_result import SyncResult, TokenRefreshResult
from integration_worker.utils.errors import SyncError, TokenRefreshError


class TestOutlookService:
    """Test suite for OutlookService."""
    
    @pytest.mark.asyncio
    async def test_sync_calendar_success(
        self, mock_db_session, mock_calendar_integration, mock_user, mock_outlook_event
    ):
        """Test successful calendar sync."""
        # Setup mocks
        service = OutlookService(mock_db_session)
        
        # Mock repository responses
        with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
            with patch.object(service, 'get_valid_access_token', return_value='test-token'):
                with patch('httpx.AsyncClient') as mock_client:
                    # Mock Microsoft Graph API response
                    mock_response = AsyncMock()
                    mock_response.json.return_value = {
                        'value': [mock_outlook_event]
                    }
                    mock_response.raise_for_status = MagicMock()
                    
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        return_value=mock_response
                    )
                    
                    # Mock user query
                    mock_user_result = AsyncMock()
                    mock_user_result.first.return_value = (mock_user.id, mock_user.firm_id)
                    mock_db_session.execute.return_value = mock_user_result
                    
                    # Mock appointment repository
                    with patch.object(service.appointments_repo, 'get_by_idempotency_key', return_value=None):
                        with patch.object(service.appointments_repo, 'create', return_value=MagicMock()):
                            # Execute
                            result = await service.sync_calendar(
                                str(mock_calendar_integration.id),
                                start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                                end_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
                            )
        
        # Assert
        assert isinstance(result, SyncResult)
        assert result.success is True
        assert result.appointments_synced == 1
        assert len(result.errors) == 0
        assert result.integration_id == str(mock_calendar_integration.id)
    
    @pytest.mark.asyncio
    async def test_sync_calendar_integration_not_found(self, mock_db_session):
        """Test sync fails when integration not found."""
        service = OutlookService(mock_db_session)
        
        with patch.object(service.calendar_repo, 'get_by_id', return_value=None):
            with pytest.raises(SyncError, match="Integration .* not found"):
                await service.sync_calendar("non-existent-id")
    
    @pytest.mark.asyncio
    async def test_sync_calendar_inactive_integration(
        self, mock_db_session, mock_calendar_integration
    ):
        """Test sync fails when integration is inactive."""
        mock_calendar_integration.is_active = False
        service = OutlookService(mock_db_session)
        
        with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
            with pytest.raises(SyncError, match="is not active"):
                await service.sync_calendar(str(mock_calendar_integration.id))
    
    @pytest.mark.asyncio
    async def test_sync_calendar_filters_cancelled_events(
        self, mock_db_session, mock_calendar_integration, mock_user
    ):
        """Test that cancelled events are filtered out."""
        service = OutlookService(mock_db_session)
        
        cancelled_event = {
            "id": "cancelled-event",
            "subject": "Cancelled Meeting",
            "start": {"dateTime": "2026-01-04T10:00:00Z", "timeZone": "UTC"},
            "end": {"dateTime": "2026-01-04T11:00:00Z", "timeZone": "UTC"},
            "isCancelled": True  # This should be filtered out
        }
        
        with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
            with patch.object(service, 'get_valid_access_token', return_value='test-token'):
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = AsyncMock()
                    mock_response.json.return_value = {'value': [cancelled_event]}
                    mock_response.raise_for_status = MagicMock()
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        return_value=mock_response
                    )
                    
                    mock_user_result = AsyncMock()
                    mock_user_result.first.return_value = (mock_user.id, mock_user.firm_id)
                    mock_db_session.execute.return_value = mock_user_result
                    
                    result = await service.sync_calendar(str(mock_calendar_integration.id))
        
        # Cancelled event should not be synced
        assert result.appointments_synced == 0
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(
        self, mock_db_session, mock_calendar_integration
    ):
        """Test successful token refresh."""
        service = OutlookService(mock_db_session)
        
        with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
            with patch('integration_worker.services.outlook_service.ConfidentialClientApplication') as mock_msal:
                # Mock MSAL token response
                mock_app = MagicMock()
                mock_app.acquire_token_by_refresh_token.return_value = {
                    'access_token': 'new-access-token',
                    'refresh_token': 'new-refresh-token',
                    'expires_in': 3600
                }
                mock_msal.return_value = mock_app
                
                result = await service.refresh_access_token(str(mock_calendar_integration.id))
        
        assert isinstance(result, TokenRefreshResult)
        assert result.success is True
        assert result.integration_id == str(mock_calendar_integration.id)
        assert result.expires_at is not None
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_no_refresh_token(
        self, mock_db_session, mock_calendar_integration
    ):
        """Test token refresh fails when no refresh token available."""
        mock_calendar_integration.refresh_token = None
        service = OutlookService(mock_db_session)
        
        with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
            with pytest.raises(TokenRefreshError, match="No refresh token available"):
                await service.refresh_access_token(str(mock_calendar_integration.id))
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_msal_error(
        self, mock_db_session, mock_calendar_integration
    ):
        """Test token refresh handles MSAL errors."""
        service = OutlookService(mock_db_session)
        
        with patch.object(service.calendar_repo, 'get_by_id', return_value=mock_calendar_integration):
            with patch('integration_worker.services.outlook_service.ConfidentialClientApplication') as mock_msal:
                mock_app = MagicMock()
                mock_app.acquire_token_by_refresh_token.return_value = {
                    'error': 'invalid_grant',
                    'error_description': 'Token has been revoked'
                }
                mock_msal.return_value = mock_app
                
                with pytest.raises(TokenRefreshError, match="Token refresh error"):
                    await service.refresh_access_token(str(mock_calendar_integration.id))
    
    @pytest.mark.asyncio
    async def test_get_valid_access_token_not_expired(
        self, mock_db_session, mock_calendar_integration
    ):
        """Test get_valid_access_token returns token when not expired."""
        # Token expires in 1 hour (not expired)
        mock_calendar_integration.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        service = OutlookService(mock_db_session)
        
        token = await service.get_valid_access_token(mock_calendar_integration)
        
        assert token == "test-access-token"
    
    @pytest.mark.asyncio
    async def test_get_valid_access_token_expired(
        self, mock_db_session, mock_calendar_integration
    ):
        """Test get_valid_access_token refreshes when token expired."""
        # Token expires in 2 minutes (will trigger refresh)
        mock_calendar_integration.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
        service = OutlookService(mock_db_session)
        
        with patch.object(service, 'refresh_access_token') as mock_refresh:
            mock_refresh.return_value = TokenRefreshResult(
                success=True,
                integration_id=str(mock_calendar_integration.id),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            # After refresh, the integration object would be updated
            mock_calendar_integration.access_token = "new-access-token"
            
            token = await service.get_valid_access_token(mock_calendar_integration)
        
        mock_refresh.assert_called_once()
        assert token == "new-access-token"
    
    def test_normalize_to_utc(self, mock_db_session):
        """Test datetime normalization to UTC."""
        service = OutlookService(mock_db_session)
        
        # Test naive datetime
        naive_dt = datetime(2026, 1, 1, 10, 0, 0)
        result = service._normalize_to_utc(naive_dt)
        assert result.tzinfo == timezone.utc
        
        # Test timezone-aware datetime
        import pytz
        eastern = pytz.timezone('US/Eastern')
        eastern_dt = eastern.localize(datetime(2026, 1, 1, 10, 0, 0))
        result = service._normalize_to_utc(eastern_dt)
        assert result.tzinfo == timezone.utc
    
    def test_generate_idempotency_key(self, mock_db_session):
        """Test idempotency key generation."""
        service = OutlookService(mock_db_session)
        
        # Short event ID
        short_id = "event-123"
        key = service._generate_idempotency_key(short_id)
        assert key == "outlook_event-123"
        assert len(key) <= 128
        
        # Long event ID (should be hashed)
        long_id = "x" * 200
        key = service._generate_idempotency_key(long_id)
        assert key.startswith("outlook_")
        assert len(key) <= 128
    
    def test_filter_events_by_date_range(self, mock_db_session):
        """Test event filtering by date range."""
        service = OutlookService(mock_db_session)
        
        events = [
            # Event within range
            {
                "id": "1",
                "start": {"dateTime": "2026-01-15T10:00:00Z"},
                "end": {"dateTime": "2026-01-15T11:00:00Z"},
                "isCancelled": False
            },
            # Event before range
            {
                "id": "2",
                "start": {"dateTime": "2025-12-01T10:00:00Z"},
                "end": {"dateTime": "2025-12-01T11:00:00Z"},
                "isCancelled": False
            },
            # Event after range
            {
                "id": "3",
                "start": {"dateTime": "2026-03-01T10:00:00Z"},
                "end": {"dateTime": "2026-03-01T11:00:00Z"},
                "isCancelled": False
            },
            # Cancelled event (should be filtered out)
            {
                "id": "4",
                "start": {"dateTime": "2026-01-20T10:00:00Z"},
                "end": {"dateTime": "2026-01-20T11:00:00Z"},
                "isCancelled": True
            },
        ]
        
        start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
        
        filtered = service._filter_events_by_date_range(events, start_date, end_date)
        
        # Only event 1 should pass (within range and not cancelled)
        assert len(filtered) == 1
        assert filtered[0]['id'] == "1"

