"""Configuration management for integration worker."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APICoreSettings(BaseSettings):
    """API Core service configuration."""
    
    model_config = SettingsConfigDict(env_prefix="CORE_API_", case_sensitive=False)
    
    url: str = Field(
        default="http://localhost:8000",
        description="Core API service URL. Env var: CORE_API_URL"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Internal API key for calling API Core internal endpoints (sent as X-Internal-API-Key). Env var: CORE_API_API_KEY"
    )


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Service info
    service_name: str = "integration-worker"
    environment: str = "development"
    
    # Database (PostgreSQL)
    database_url: str
    
    # Redis (Celery broker + result backend)
    redis_url: str = "redis://localhost:6379/0"
    
    # API Core service (using nested settings for consistent env var naming)
    api_core: APICoreSettings = Field(default_factory=APICoreSettings)
    
    # Backward compatibility properties
    @property
    def api_core_url(self) -> str:
        """Backward compatibility: get API Core URL."""
        return self.api_core.url
    
    @property
    def api_core_api_key(self) -> Optional[str]:
        """Backward compatibility: get API Core API key."""
        return self.api_core.api_key
    
    # Azure AD / Microsoft Graph
    azure_ad_client_id: str
    azure_ad_tenant_id: str
    azure_ad_client_secret: str
    
    # Google Calendar API
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    
    # Clio API (Phase 6)
    clio_client_id: Optional[str] = None
    clio_client_secret: Optional[str] = None
    
    # Webhook settings
    webhook_base_url: Optional[str] = "http://localhost:8080"
    webhook_secret: Optional[str] = None  # For validating webhook signatures
    
    # Sync settings
    sync_lookback_days: int = 30  # How far back to sync
    sync_lookahead_days: int = 90  # How far ahead to sync
    sync_batch_size: int = 100  # Max events per sync
    
    # Retry settings
    max_retries: int = 3
    retry_backoff_seconds: int = 60
    
    # Logging
    log_level: str = "INFO"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

