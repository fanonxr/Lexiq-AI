"""Tests for configuration management."""

import os
import pytest
from api_core.config import (
    Settings,
    DatabaseSettings,
    AzureADB2CSettings,
    JWTSettings,
    CorsSettings,
    Environment,
    get_settings,
)


def test_database_settings():
    """Test database settings."""
    settings = DatabaseSettings(url="postgresql://user:pass@localhost/db")
    assert settings.url == "postgresql://user:pass@localhost/db"
    assert settings.pool_size == 10
    assert settings.max_overflow == 20


def test_database_settings_invalid_url():
    """Test database settings with invalid URL."""
    with pytest.raises(ValueError, match="Database URL must start with"):
        DatabaseSettings(url="invalid://url")


def test_azure_ad_b2c_settings():
    """Test Azure AD B2C settings."""
    settings = AzureADB2CSettings(
        tenant_id="test-tenant",
        client_id="test-client",
        policy_signup_signin="B2C_1_signup_signin",
    )
    assert settings.tenant_id == "test-tenant"
    assert settings.client_id == "test-client"
    assert settings.is_configured is True
    assert "test-tenant" in settings.authority


def test_azure_ad_b2c_settings_not_configured(monkeypatch):
    """Test Azure AD B2C settings when not configured."""
    # Clear any environment variables that might affect this test
    monkeypatch.delenv("AZURE_AD_B2C_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_AD_B2C_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_AD_B2C_POLICY_SIGNUP_SIGNIN", raising=False)
    
    settings = AzureADB2CSettings()
    assert settings.is_configured is False
    assert settings.authority is None


def test_jwt_settings():
    """Test JWT settings."""
    settings = JWTSettings(secret_key="test-secret")
    assert settings.secret_key == "test-secret"
    assert settings.algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30


def test_cors_settings():
    """Test CORS settings."""
    # Test with string (using origins_str which is the actual field name)
    settings = CorsSettings(origins_str="http://localhost:3000,http://localhost:3001")
    assert len(settings.origins) == 2
    assert "http://localhost:3000" in settings.origins
    assert "http://localhost:3001" in settings.origins

    # Test with single origin string
    settings = CorsSettings(origins_str="http://localhost:3000")
    assert len(settings.origins) == 1
    assert "http://localhost:3000" in settings.origins


def test_settings_environment():
    """Test settings environment parsing."""
    settings = Settings(environment="production")
    assert settings.environment == Environment.PRODUCTION
    assert settings.is_production is True
    assert settings.is_development is False

    settings = Settings(environment="development")
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.is_development is True


def test_settings_log_level():
    """Test log level validation."""
    settings = Settings(log_level="info")
    assert settings.log_level == "INFO"

    with pytest.raises(ValueError, match="Log level must be one of"):
        Settings(log_level="INVALID")


def test_get_settings_singleton():
    """Test that get_settings returns a singleton."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_settings_from_env(monkeypatch):
    """Test loading settings from environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
    monkeypatch.setenv("CORS_ORIGINS_STR", "http://test.com,http://test2.com")

    settings = Settings()
    assert settings.environment == Environment.STAGING
    assert settings.debug is True
    assert settings.database.url == "postgresql://test:test@localhost/testdb"
    assert len(settings.cors.origins) == 2
