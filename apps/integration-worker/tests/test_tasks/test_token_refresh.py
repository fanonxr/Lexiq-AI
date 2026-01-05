"""Tests for token refresh tasks."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from integration_worker.tasks.token_refresh import refresh_expiring_tokens


class TestTokenRefreshTasks:
    """Test suite for token refresh tasks."""
    
    def test_refresh_expiring_tokens_task_signature(self):
        """Test that refresh_expiring_tokens task is properly configured."""
        assert refresh_expiring_tokens.name == "integration_worker.tasks.token_refresh.refresh_expiring_tokens"
    
    @patch('integration_worker.tasks.token_refresh.get_session')
    @patch('integration_worker.tasks.token_refresh.OutlookService')
    def test_refresh_expiring_tokens_success(self, mock_service_class, mock_get_session):
        """Test successful token refresh task."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock integration with expiring token
        mock_integration = MagicMock()
        mock_integration.id = str(uuid.uuid4())
        mock_integration.integration_type = "outlook"
        
        with patch('integration_worker.tasks.token_refresh.CalendarIntegrationRepository') as mock_repo_class:
            mock_repo = MagicMock()
            
            async def mock_get_expiring():
                return [mock_integration]
            
            mock_repo.get_with_expiring_tokens = mock_get_expiring
            mock_repo_class.return_value = mock_repo
            
            # Mock service
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            
            async def mock_refresh(*args, **kwargs):
                return mock_result
            
            mock_service.refresh_access_token = mock_refresh
            mock_service_class.return_value = mock_service
            
            result = refresh_expiring_tokens()
        
        assert result['refreshed'] == 1
        assert result['errors'] == 0
    
    @patch('integration_worker.tasks.token_refresh.get_session')
    def test_refresh_expiring_tokens_no_integrations(self, mock_get_session):
        """Test refresh task when no integrations have expiring tokens."""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        with patch('integration_worker.tasks.token_refresh.CalendarIntegrationRepository') as mock_repo_class:
            mock_repo = MagicMock()
            
            async def mock_get_expiring():
                return []
            
            mock_repo.get_with_expiring_tokens = mock_get_expiring
            mock_repo_class.return_value = mock_repo
            
            result = refresh_expiring_tokens()
        
        assert result['refreshed'] == 0
        assert result['errors'] == 0

