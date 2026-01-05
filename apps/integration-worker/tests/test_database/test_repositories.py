"""Tests for database repositories."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import uuid

from integration_worker.database.repositories import (
    CalendarIntegrationRepository,
    AppointmentsRepository,
)


class TestCalendarIntegrationRepository:
    """Test suite for CalendarIntegrationRepository."""
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_db_session, mock_calendar_integration):
        """Test get_by_id method."""
        repo = CalendarIntegrationRepository(mock_db_session)
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_integration
        mock_db_session.execute.return_value = mock_result
        
        result = await repo.get_by_id(str(mock_calendar_integration.id))
        
        assert result == mock_calendar_integration
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_user_and_type(self, mock_db_session, mock_calendar_integration):
        """Test get_by_user_and_type method."""
        repo = CalendarIntegrationRepository(mock_db_session)
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_calendar_integration
        mock_db_session.execute.return_value = mock_result
        
        result = await repo.get_by_user_and_type(
            str(mock_calendar_integration.user_id),
            "outlook"
        )
        
        assert result == mock_calendar_integration
    
    @pytest.mark.asyncio
    async def test_get_all_active(self, mock_db_session, mock_calendar_integration):
        """Test get_all_active method."""
        repo = CalendarIntegrationRepository(mock_db_session)
        
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_calendar_integration]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result
        
        result = await repo.get_all_active()
        
        assert len(result) == 1
        assert result[0] == mock_calendar_integration
    
    @pytest.mark.asyncio
    async def test_get_with_expiring_tokens(self, mock_db_session, mock_calendar_integration):
        """Test get_with_expiring_tokens method."""
        repo = CalendarIntegrationRepository(mock_db_session)
        
        expiring_integration = mock_calendar_integration
        expiring_integration.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
        
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [expiring_integration]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result
        
        threshold = datetime.now(timezone.utc) + timedelta(hours=24)
        result = await repo.get_with_expiring_tokens(threshold)
        
        assert len(result) == 1
        assert result[0] == expiring_integration


class TestAppointmentsRepository:
    """Test suite for AppointmentsRepository."""
    
    @pytest.mark.asyncio
    async def test_get_by_idempotency_key(self, mock_db_session, mock_appointment):
        """Test get_by_idempotency_key method."""
        repo = AppointmentsRepository(mock_db_session)
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_appointment
        mock_db_session.execute.return_value = mock_result
        
        result = await repo.get_by_idempotency_key("outlook_test-123")
        
        assert result == mock_appointment
    
    @pytest.mark.asyncio
    async def test_create_appointment(self, mock_db_session):
        """Test create method."""
        repo = AppointmentsRepository(mock_db_session)
        
        with patch('integration_worker.database.repositories.Appointment') as mock_appointment_class:
            mock_appointment = MagicMock()
            mock_appointment.id = str(uuid.uuid4())
            mock_appointment_class.return_value = mock_appointment
            
            result = await repo.create(
                firm_id="firm-123",
                title="Test Meeting",
                start_at=datetime.now(timezone.utc),
                duration_minutes=60,
            )
        
        # Session methods should be called
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

