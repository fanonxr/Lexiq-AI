"""Tests for Celery application configuration."""

import pytest


def test_celery_app_imports():
    """Test that Celery app can be imported."""
    from integration_worker.celery_app import app
    
    assert app is not None
    assert app.main == "integration_worker"


def test_celery_app_configuration():
    """Test Celery app configuration."""
    from integration_worker.celery_app import app
    
    assert app.conf.task_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert app.conf.result_serializer == "json"
    assert app.conf.timezone == "UTC"
    assert app.conf.enable_utc is True
    assert app.conf.task_time_limit == 300
    assert app.conf.task_soft_time_limit == 240


def test_celery_beat_schedule():
    """Test that Celery Beat schedule is configured correctly."""
    from integration_worker.celery_app import app
    
    beat_schedule = app.conf.beat_schedule
    
    # Check that all scheduled tasks are configured
    assert "sync-all-calendars" in beat_schedule
    assert "refresh-expiring-tokens" in beat_schedule
    assert "cleanup-sync-logs" in beat_schedule
    
    # Verify task names
    assert beat_schedule["sync-all-calendars"]["task"] == \
        "integration_worker.tasks.calendar_sync.sync_all_calendars"
    assert beat_schedule["refresh-expiring-tokens"]["task"] == \
        "integration_worker.tasks.token_refresh.refresh_expiring_tokens"
    assert beat_schedule["cleanup-sync-logs"]["task"] == \
        "integration_worker.tasks.cleanup.cleanup_old_sync_logs"


def test_tasks_are_registered():
    """Test that tasks are registered with Celery."""
    from integration_worker.celery_app import app
    
    # Check that task modules are included
    task_names = [task for task in app.tasks.keys()]
    
    # Should include our custom tasks (once they're imported)
    # This is a basic check that the app is configured correctly
    assert len(task_names) > 0

