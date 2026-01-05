"""Pytest configuration and fixtures for integration worker tests."""

import pytest
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import uuid


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from integration_worker.config import Settings
    
    return Settings(
        service_name="integration-worker-test",
        environment="test",
        database_url="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/1",  # Use DB 1 for testing
        api_core_url="http://localhost:8000",
        azure_ad_client_id="test-client-id",
        azure_ad_tenant_id="test-tenant-id",
        azure_ad_client_secret="test-client-secret",
        log_level="DEBUG",
    )


@pytest.fixture
def mock_calendar_integration():
    """Mock CalendarIntegration model instance."""
    mock = MagicMock()
    mock.id = str(uuid.uuid4())
    mock.user_id = str(uuid.uuid4())
    mock.integration_type = "outlook"
    mock.access_token = "test-access-token"
    mock.refresh_token = "test-refresh-token"
    mock.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    mock.calendar_id = "test-calendar-id"
    mock.email = "test@example.com"
    mock.is_active = True
    mock.last_synced_at = None
    mock.sync_error = None
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    return mock


@pytest.fixture
def mock_user():
    """Mock User model instance."""
    mock = MagicMock()
    mock.id = str(uuid.uuid4())
    mock.firm_id = str(uuid.uuid4())
    mock.email = "user@example.com"
    mock.name = "Test User"
    return mock


@pytest.fixture
def mock_appointment():
    """Mock Appointment model instance."""
    mock = MagicMock()
    mock.id = str(uuid.uuid4())
    mock.firm_id = str(uuid.uuid4())
    mock.created_by_user_id = str(uuid.uuid4())
    mock.title = "Test Appointment"
    mock.start_at = datetime.now(timezone.utc)
    mock.end_at = datetime.now(timezone.utc) + timedelta(hours=1)
    mock.duration_minutes = 60
    mock.status = "booked"
    mock.idempotency_key = "outlook_test-event-123"
    return mock


@pytest.fixture
def mock_outlook_event():
    """Mock Outlook calendar event from Microsoft Graph API."""
    return {
        "id": "test-event-123",
        "subject": "Test Meeting",
        "start": {
            "dateTime": "2026-01-04T10:00:00Z",
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": "2026-01-04T11:00:00Z",
            "timeZone": "UTC"
        },
        "organizer": {
            "emailAddress": {
                "name": "John Doe",
                "address": "john@example.com"
            }
        },
        "attendees": [],
        "isCancelled": False
    }


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def celery_config():
    """Celery configuration for testing."""
    return {
        'broker_url': 'redis://localhost:6379/1',
        'result_backend': 'redis://localhost:6379/1',
        'task_always_eager': True,  # Execute tasks synchronously for testing
        'task_eager_propagates': True,  # Propagate exceptions in eager mode
    }


@pytest.fixture
def celery_app(celery_config):
    """Celery app fixture for testing tasks."""
    from integration_worker.celery_app import app
    app.conf.update(celery_config)
    return app

