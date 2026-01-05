"""Configuration management using pydantic-settings."""

import json
import os
from enum import Enum
from typing import Annotated, List, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_", case_sensitive=False)

    url: str = Field(..., description="Database connection URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    echo: bool = Field(default=False, description="Echo SQL queries (for debugging)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("Database URL must start with postgresql:// or postgresql+psycopg2://")
        return v


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", case_sensitive=False)

    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    password: Optional[str] = Field(default=None, description="Redis password")
    decode_responses: bool = Field(default=True, description="Decode responses as strings")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(default=5, description="Socket connect timeout in seconds")


class RabbitMQSettings(BaseSettings):
    """RabbitMQ configuration (used to publish ingestion jobs)."""

    model_config = SettingsConfigDict(env_prefix="RABBITMQ_", case_sensitive=False)

    url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )
    exchange_name: str = Field(
        default="document-ingestion-exchange",
        description="Exchange name for document ingestion jobs",
    )
    routing_key: str = Field(
        default="document.ingestion",
        description="Routing key for ingestion messages",
    )


class AzureADB2CSettings(BaseSettings):
    """Azure AD B2C / Microsoft Entra ID configuration.
    
    Supports both:
    - Azure AD B2C: Uses b2clogin.com and requires policy
    - Microsoft Entra ID (Azure AD): Uses login.microsoftonline.com, no policy needed
    """

    model_config = SettingsConfigDict(env_prefix="AZURE_AD_B2C_", case_sensitive=False)

    tenant_id: Optional[str] = Field(default=None, description="Azure AD B2C / Entra ID tenant ID")
    client_id: Optional[str] = Field(default=None, description="Azure AD B2C / Entra ID client ID")
    client_secret: Optional[str] = Field(default=None, description="Azure AD B2C client secret (optional)")
    policy_signup_signin: Optional[str] = Field(
        default=None, description="Azure AD B2C sign-up/sign-in policy name (only needed for B2C, not Entra ID)"
    )
    instance: str = Field(
        default="https://login.microsoftonline.com",
        description="Instance URL. For Entra ID: 'https://login.microsoftonline.com'. For B2C: 'https://{tenant}.b2clogin.com'",
    )
    use_b2c: bool = Field(
        default=False,
        description="Whether to use Azure AD B2C (True) or Entra ID (False). Auto-detected if policy is provided.",
    )

    @property
    def is_b2c(self) -> bool:
        """Determine if using Azure AD B2C based on instance URL or policy."""
        if self.use_b2c:
            return True
        if self.policy_signup_signin:
            return True
        # Check if instance contains b2clogin.com
        return "b2clogin.com" in self.instance.lower()

    @property
    def authority(self) -> Optional[str]:
        """Get the authority URL for Azure AD B2C or Entra ID."""
        if not self.tenant_id:
            return None
        
        if self.is_b2c:
            # Azure AD B2C format: https://{tenant}.b2clogin.com/{tenant}/{policy}
            if not self.policy_signup_signin:
                return None
            instance_url = self.instance.format(tenant=self.tenant_id) if "{tenant}" in self.instance else self.instance
            return f"{instance_url}/{self.tenant_id}/{self.policy_signup_signin}"
        else:
            # Entra ID format: https://login.microsoftonline.com/{tenant-id}
            return f"{self.instance}/{self.tenant_id}"

    @property
    def is_configured(self) -> bool:
        """Check if Azure AD B2C or Entra ID is properly configured."""
        if not self.tenant_id or not self.client_id:
            return False
        # For B2C, policy is required. For Entra ID, it's not.
        if self.is_b2c:
            return bool(self.policy_signup_signin)
        return True  # Entra ID only needs tenant_id and client_id


class AzureKeyVaultSettings(BaseSettings):
    """Azure Key Vault configuration."""

    model_config = SettingsConfigDict(env_prefix="AZURE_KEY_VAULT_", case_sensitive=False)

    url: Optional[str] = Field(default=None, description="Azure Key Vault URL")
    enabled: bool = Field(default=False, description="Enable Azure Key Vault integration")

    @property
    def is_configured(self) -> bool:
        """Check if Azure Key Vault is configured."""
        return self.enabled and bool(self.url)


class GoogleSettings(BaseSettings):
    """Google OAuth configuration for Google Calendar integration."""

    model_config = SettingsConfigDict(env_prefix="GOOGLE_", case_sensitive=False)

    client_id: Optional[str] = Field(default=None, description="Google OAuth client ID")
    client_secret: Optional[str] = Field(default=None, description="Google OAuth client secret")

    @property
    def is_configured(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.client_id and self.client_secret)


class StorageSettings(BaseSettings):
    """Azure Blob Storage configuration for knowledge base files."""

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_", 
        case_sensitive=False,
        # pydantic-settings uses field names (not aliases) for env var lookup
        # With env_prefix="STORAGE_" and case_sensitive=False:
        # - Field "connection_string" looks for: STORAGE_connection_string, STORAGE_CONNECTION_STRING, etc.
        # - Field "account_name" looks for: STORAGE_account_name, STORAGE_ACCOUNT_NAME, etc.
        populate_by_name=True,  # Allow both field name and alias for JSON/dict input
    )

    account_name: Optional[str] = Field(
        default=None, 
        description="Azure Storage Account name",
        # Alias for JSON/dict serialization, env var is STORAGE_ACCOUNT_NAME (case-insensitive)
    )
    account_key: Optional[str] = Field(
        default=None, 
        description="Azure Storage Account key (use Managed Identity instead)",
    )
    connection_string: Optional[str] = Field(
        default=None,
        description="Azure Storage connection string (use Managed Identity instead)",
    )
    use_managed_identity: bool = Field(
        default=False,  # Changed default to False for local development
        description="Use Managed Identity for authentication (recommended for production)",
    )
    max_file_size_mb: int = Field(
        default=100, description="Maximum file size in MB"
    )
    allowed_file_types: List[str] = Field(
        default_factory=lambda: ["pdf", "docx", "txt", "md"],
        description="Allowed file types for upload",
    )

    @property
    def is_configured(self) -> bool:
        """Check if storage is configured."""
        return bool(self.account_name) and (
            bool(self.connection_string) or bool(self.account_key) or self.use_managed_identity
        )


class JWTSettings(BaseSettings):
    """JWT token configuration."""

    model_config = SettingsConfigDict(env_prefix="JWT_", case_sensitive=False)

    secret_key: str = Field(
        default="change-me-in-production",
        description="JWT secret key (for local development only)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration time in days"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is not default in production."""
        # Note: Environment check will be done at Settings level
        if v == "change-me-in-production":
            import warnings

            warnings.warn(
                "Using default JWT_SECRET_KEY. This should be changed in production. "
                "Use Azure Key Vault or a secure secret management system.",
                UserWarning,
            )
        return v


class CorsSettings(BaseSettings):
    """CORS configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        case_sensitive=False,
    )

    # Store as strings to avoid JSON parsing issues
    origins_str: str = Field(
        default="http://localhost:3000",
        description="Allowed CORS origins (comma-separated string). Env var: CORS_origins",
    )
    allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    allow_methods_str: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS,PATCH",
        description="Allowed HTTP methods (comma-separated string). Env var: CORS_allow_methods",
    )
    allow_headers_str: str = Field(
        default="*",
        description="Allowed HTTP headers (comma-separated string). Env var: CORS_allow_headers",
    )
    max_age: int = Field(default=3600, description="CORS preflight cache max age in seconds")

    @property
    def origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.origins_str.split(",") if origin.strip()]

    @property
    def allow_methods(self) -> List[str]:
        """Get allowed HTTP methods as a list."""
        return [method.strip() for method in self.allow_methods_str.split(",") if method.strip()]

    @property
    def allow_headers(self) -> List[str]:
        """Get allowed HTTP headers as a list."""
        return [header.strip() for header in self.allow_headers_str.split(",") if header.strip()]


class ServerSettings(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload (development only)")


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        # Note: In Docker, env_file is loaded by docker-compose.yml
        # For local development, pydantic-settings will look for .env in the current working directory
        # The env_file path is relative to where the Python process runs (inside container: /app)
        # Docker Compose loads apps/api-core/.env and makes variables available as environment variables
        # So we don't need to specify env_file here - environment variables take precedence
        # However, we can also explicitly load from .env file as a fallback
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="api-core", description="Application name")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API settings
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")

    # Internal service-to-service auth (protect internal endpoints)
    internal_api_key_enabled: bool = Field(
        default=False,
        description="Enable API-key auth for internal service endpoints. Env var: INTERNAL_API_KEY_ENABLED",
    )
    internal_api_key: Optional[str] = Field(
        default=None,
        description="Shared secret API key for internal services (sent as X-Internal-API-Key). Env var: INTERNAL_API_KEY",
    )

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    azure_ad_b2c: AzureADB2CSettings = Field(default_factory=AzureADB2CSettings)
    azure_key_vault: AzureKeyVaultSettings = Field(default_factory=AzureKeyVaultSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)

    @field_validator("environment", mode="before")
    @classmethod
    def parse_environment(cls, v):
        """Parse environment from string."""
        if isinstance(v, str):
            try:
                return Environment(v.lower())
            except ValueError:
                return Environment.DEVELOPMENT
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment == Environment.STAGING

    def load_secrets_from_key_vault(self) -> None:
        """Load secrets from Azure Key Vault if configured."""
        if not self.azure_key_vault.is_configured:
            return

        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=self.azure_key_vault.url, credential=credential)

            # Load secrets and update settings
            # This is a placeholder - implement based on your secret naming convention
            secret_mapping = {
                "database-url": ("database", "url"),
                "jwt-secret-key": ("jwt", "secret_key"),
                "azure-ad-b2c-client-secret": ("azure_ad_b2c", "client_secret"),
            }

            for secret_name, (section, key) in secret_mapping.items():
                try:
                    secret = client.get_secret(secret_name)
                    if section == "database":
                        # Create new DatabaseSettings with updated URL
                        self.database = DatabaseSettings(url=secret.value)
                    elif section == "jwt":
                        # Create new JWTSettings with updated secret key
                        self.jwt = JWTSettings(secret_key=secret.value)
                    elif section == "azure_ad_b2c":
                        # Update client secret
                        self.azure_ad_b2c.client_secret = secret.value
                except Exception as e:
                    # Log warning but don't fail - secrets might not exist
                    import logging

                    logging.warning(f"Failed to load secret {secret_name} from Key Vault: {e}")

        except ImportError:
            import logging

            logging.warning(
                "Azure Key Vault libraries not installed. "
                "Install with: pip install azure-keyvault-secrets azure-identity"
            )
        except Exception as e:
            import logging

            logging.error(f"Failed to load secrets from Azure Key Vault: {e}")

    def validate_production_settings(self) -> None:
        """Validate that production settings are secure."""
        if self.is_production:
            if self.jwt.secret_key == "change-me-in-production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a secure value in production. "
                    "Use Azure Key Vault or a secure secret management system."
                )
            if self.debug:
                raise ValueError("DEBUG must be False in production")
            if not self.azure_key_vault.is_configured:
                import warnings

                warnings.warn(
                    "Azure Key Vault is not configured in production. "
                    "Consider using it for secure secret management.",
                    UserWarning,
                )
            if self.internal_api_key_enabled and not self.internal_api_key:
                raise ValueError(
                    "INTERNAL_API_KEY must be set when INTERNAL_API_KEY_ENABLED=true (internal endpoints protection)."
                )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        import logging
        import os
        logger = logging.getLogger(__name__)
        
        # Debug: Log storage-related environment variables
        storage_env_vars = {k: v for k, v in os.environ.items() if k.startswith("STORAGE_")}
        if storage_env_vars:
            logger.debug(f"Storage environment variables found: {list(storage_env_vars.keys())}")
            # Log connection string preview (first 50 chars) for debugging
            if "STORAGE_CONNECTION_STRING" in storage_env_vars:
                conn_str = storage_env_vars["STORAGE_CONNECTION_STRING"]
                logger.debug(f"STORAGE_CONNECTION_STRING length: {len(conn_str)}, preview: {conn_str[:50]}...")
        else:
            logger.warning("No STORAGE_* environment variables found")
        
        _settings = Settings()
        
        # Debug: Log what was actually loaded
        logger.debug(
            f"Storage settings loaded - "
            f"account_name: {bool(_settings.storage.account_name)}, "
            f"connection_string: {bool(_settings.storage.connection_string)}, "
            f"use_managed_identity: {_settings.storage.use_managed_identity}"
        )
        
        # Load secrets from Key Vault if configured
        if _settings.azure_key_vault.is_configured:
            _settings.load_secrets_from_key_vault()
        # Validate production settings
        try:
            _settings.validate_production_settings()
        except ValueError as e:
            logging.error(f"Configuration validation failed: {e}")
            if _settings.is_production:
                raise  # Fail fast in production
        
        # Log Azure AD configuration status for debugging
        if _settings.azure_ad_b2c.is_configured:
            auth_type = "Azure AD B2C" if _settings.azure_ad_b2c.is_b2c else "Microsoft Entra ID"
            logger.info(f"{auth_type} is configured: tenant_id={_settings.azure_ad_b2c.tenant_id[:8]}..., client_id={_settings.azure_ad_b2c.client_id[:8]}...")
        else:
            logger.warning(
                f"Azure AD / Entra ID is not configured. "
                f"tenant_id={'set' if _settings.azure_ad_b2c.tenant_id else 'missing'}, "
                f"client_id={'set' if _settings.azure_ad_b2c.client_id else 'missing'}"
            )
    return _settings


# Convenience function to get settings
settings = get_settings()
