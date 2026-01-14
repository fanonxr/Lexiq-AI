"""Tests for calendar sync tasks."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from integration_worker.tasks.calendar_sync import (
    sync_outlook_calendar,
    sync_all_calendars,
    sync_google_calendar,
)


class TestCalendarSyncTasks:
    """Test suite for calendar sync tasks."""
    
    def test_sync_outlook_calendar_task_signature(self):
        """Test that sync_outlook_calendar task is properly configured."""
        assert sync_outlook_calendar.name == "integration_worker.tasks.calendar_sync.sync_outlook_calendar"
        assert sync_outlook_calendar.max_retries == 3
        assert sync_outlook_calendar.default_retry_delay == 60
    
    @patch('integration_worker.tasks.calendar_sync.get_session')
    @patch('integration_worker.tasks.calendar_sync.OutlookService')
    def test_sync_outlook_calendar_success(self, mock_service_class, mock_get_session):
        """Test successful Outlook calendar sync task."""
        # Setup mocks
        integration_id = str(uuid.uuid4())
        
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.appointments_synced = 5
        mock_result.appointments_updated = 2
        mock_result.appointments_deleted = 1
        mock_result.total_changes = 8
        mock_result.errors = []
        
        async def mock_sync(*args, **kwargs):
            return mock_result
        
        mock_service.sync_calendar = mock_sync
        mock_service_class.return_value = mock_service
        
        # Execute task (synchronously in eager mode)
        result = sync_outlook_calendar(integration_id)
        
        # Assert
        assert result['success'] is True
        assert result['integration_id'] == integration_id
        assert result['appointments_synced'] == 5
        assert result['total_changes'] == 8
    
    @patch('integration_worker.tasks.calendar_sync.get_session')
    def test_sync_all_calendars_task(self, mock_get_session):
        """Test sync_all_calendars task."""
        # Setup mocks
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock repository with 2 active integrations
        mock_integration1 = MagicMock()
        mock_integration1.id = str(uuid.uuid4())
        mock_integration1.integration_type = "outlook"
        
        mock_integration2 = MagicMock()
        mock_integration2.id = str(uuid.uuid4())
        mock_integration2.integration_type = "google"
        
        with patch('integration_worker.database.repositories.CalendarIntegrationRepository') as mock_repo_class:
            mock_repo = MagicMock()
            
            async def mock_get_all_active():
                return [mock_integration1, mock_integration2]
            
            mock_repo.get_all_active = mock_get_all_active
            mock_repo_class.return_value = mock_repo
            
            with patch.object(sync_outlook_calendar, 'delay') as mock_outlook_delay:
                with patch.object(sync_google_calendar, 'delay') as mock_google_delay:
                    result = sync_all_calendars()
        
        # Should trigger sync for both outlook and google integrations
        assert result['synced'] == 2  # Both outlook and google
        assert result['errors'] == 0
        mock_outlook_delay.assert_called_once()
        mock_google_delay.assert_called_once()
    
    def test_sync_google_calendar_task_signature(self):
        """Test that sync_google_calendar task is properly configured."""
        assert sync_google_calendar.name == "integration_worker.tasks.calendar_sync.sync_google_calendar"
        assert sync_google_calendar.max_retries == 3

