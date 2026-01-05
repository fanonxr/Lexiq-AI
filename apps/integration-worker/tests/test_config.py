"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from integration_worker.config import Settings, get_settings


def test_settings_defaults():
    """Test that settings have correct defaults."""
    # Create settings with minimal required fields
    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        azure_ad_client_id="test-client-id",
        azure_ad_tenant_id="test-tenant-id",
        azure_ad_client_secret="test-secret",
    )
    
    assert settings.service_name == "integration-worker"
    assert settings.environment == "development"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.sync_lookback_days == 30
    assert settings.sync_lookahead_days == 90
    assert settings.max_retries == 3
    assert settings.log_level == "INFO"


def test_settings_from_env(monkeypatch):
    """Test that settings load from environment variables."""
    monkeypatch.setenv("SERVICE_NAME", "test-worker")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")
    monkeypatch.setenv("REDIS_URL", "redis://test:6379/0")
    monkeypatch.setenv("AZURE_AD_CLIENT_ID", "env-client-id")
    monkeypatch.setenv("AZURE_AD_TENANT_ID", "env-tenant-id")
    monkeypatch.setenv("AZURE_AD_CLIENT_SECRET", "env-secret")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    # Clear singleton
    import integration_worker.config
    integration_worker.config._settings = None
    
    settings = get_settings()
    
    assert settings.service_name == "test-worker"
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.azure_ad_client_id == "env-client-id"


def test_settings_required_fields():
    """Test that required fields raise validation error when missing."""
    with pytest.raises(ValidationError):
        Settings()  # Should fail without required fields

