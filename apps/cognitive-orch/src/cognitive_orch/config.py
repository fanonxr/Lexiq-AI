"""Configuration management using pydantic-settings."""

import warnings
from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMSettings(BaseSettings):
    """LLM configuration for model routing."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    default_model_name: str = Field(
        default="azure/gpt-4o",
        description="Default LLM model name (LiteLLM format). Env var: DEFAULT_MODEL_NAME",
    )
    fallback_model_name: str = Field(
        default="anthropic/claude-3-haiku",
        description="Fallback LLM model name (LiteLLM format). Env var: FALLBACK_MODEL_NAME",
    )
    enable_fallbacks: bool = Field(
        default=True,
        description="Enable automatic fallback to secondary model on failure. Env var: ENABLE_FALLBACKS",
    )

    # Azure OpenAI
    azure_api_key: Optional[str] = Field(
        default=None, description="Azure OpenAI API key. Env var: AZURE_API_KEY"
    )
    azure_api_base: Optional[str] = Field(
        default=None, description="Azure OpenAI endpoint URL. Env var: AZURE_API_BASE"
    )
    azure_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version. Env var: AZURE_API_VERSION",
    )

    # Anthropic
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key. Env var: ANTHROPIC_API_KEY"
    )

    # AWS Bedrock (optional)
    aws_access_key_id: Optional[str] = Field(
        default=None, description="AWS access key ID for Bedrock. Env var: AWS_ACCESS_KEY_ID"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret access key for Bedrock. Env var: AWS_SECRET_ACCESS_KEY",
    )
    aws_region: Optional[str] = Field(
        default=None, description="AWS region for Bedrock. Env var: AWS_REGION"
    )

    # Groq (optional)
    groq_api_key: Optional[str] = Field(
        default=None, description="Groq API key. Env var: GROQ_API_KEY"
    )

    @property
    def has_azure_openai(self) -> bool:
        """Check if Azure OpenAI is configured."""
        return bool(self.azure_api_key and self.azure_api_base)

    @property
    def has_anthropic(self) -> bool:
        """Check if Anthropic is configured."""
        return bool(self.anthropic_api_key)

    @property
    def has_aws_bedrock(self) -> bool:
        """Check if AWS Bedrock is configured."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key and self.aws_region)

    @property
    def has_groq(self) -> bool:
        """Check if Groq is configured."""
        return bool(self.groq_api_key)


class RedisSettings(BaseSettings):
    """Redis configuration for conversation state."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", case_sensitive=False)

    url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    password: Optional[str] = Field(default=None, description="Redis password")
    decode_responses: bool = Field(
        default=True, description="Decode responses as strings"
    )
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(
        default=5, description="Socket connect timeout in seconds"
    )
    conversation_ttl: int = Field(
        default=3600,
        description="Conversation state TTL in seconds. Env var: REDIS_conversation_ttl",
    )


class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration."""

    model_config = SettingsConfigDict(env_prefix="QDRANT_", case_sensitive=False)

    url: str = Field(
        default="http://localhost:6333", description="Qdrant connection URL"
    )
    api_key: Optional[str] = Field(
        default=None, description="Qdrant API key (for Qdrant Cloud). Env var: QDRANT_api_key"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    prefer_grpc: bool = Field(
        default=False, description="Prefer gRPC over REST API"
    )

    @property
    def is_cloud(self) -> bool:
        """Check if using Qdrant Cloud (has API key)."""
        return bool(self.api_key)


class ServerSettings(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    host: str = Field(default="0.0.0.0", description="Server host. Env var: HOST")
    port: int = Field(default=8001, description="HTTP server port. Env var: PORT")
    grpc_port: int = Field(
        default=50051, description="gRPC server port. Env var: GRPC_PORT"
    )
    reload: bool = Field(
        default=False, description="Enable auto-reload (development only)"
    )


class IntegrationSettings(BaseSettings):
    """External service integration configuration."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    # Core API
    core_api_url: str = Field(
        default="http://localhost:8000",
        description="Core API service URL. Env var: CORE_API_URL",
    )
    core_api_timeout: int = Field(
        default=30, description="Core API request timeout in seconds. Env var: CORE_API_TIMEOUT"
    )
    core_api_api_key: Optional[str] = Field(
        default=None,
        description="Optional internal API key for Core API (sent as X-Internal-API-Key). Env var: CORE_API_API_KEY",
    )

    # Integration Worker
    integration_worker_url: str = Field(
        default="http://localhost:8002",
        description="Integration Worker service URL. Env var: INTEGRATION_WORKER_URL",
    )
    integration_worker_timeout: int = Field(
        default=30,
        description="Integration Worker request timeout in seconds. Env var: INTEGRATION_WORKER_TIMEOUT",
    )


class DatabaseSettings(BaseSettings):
    """Database configuration for client memory storage."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_", case_sensitive=False)

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lexiq",
        description="Database connection URL. Env var: DATABASE_URL",
    )
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    echo: bool = Field(default=False, description="Echo SQL queries (debug mode)")

    @property
    def async_url(self) -> str:
        """Get async database URL."""
        url = self.url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        return url


class ContextWindowSettings(BaseSettings):
    """Context window and conversation history configuration."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    max_context_window: int = Field(
        default=8000,
        description="Maximum context window size in tokens. Env var: MAX_CONTEXT_WINDOW",
    )
    max_history_messages: int = Field(
        default=50,
        description="Maximum number of messages to keep in conversation history. Env var: MAX_HISTORY_MESSAGES",
    )


class CorsSettings(BaseSettings):
    """CORS configuration."""

    model_config = SettingsConfigDict(env_prefix="CORS_", case_sensitive=False)

    # Store as strings to avoid JSON parsing issues
    origins_str: str = Field(
        default="http://localhost:3000",
        description="Allowed CORS origins (comma-separated string). Env var: CORS_origins",
    )
    allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS"
    )
    allow_methods_str: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS,PATCH",
        description="Allowed HTTP methods (comma-separated string). Env var: CORS_allow_methods",
    )
    allow_headers_str: str = Field(
        default="*",
        description="Allowed HTTP headers (comma-separated string). Env var: CORS_allow_headers",
    )
    max_age: int = Field(
        default=3600, description="CORS preflight cache max age in seconds"
    )

    @property
    def origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.origins_str.split(",") if origin.strip()]

    @property
    def allow_methods(self) -> List[str]:
        """Get allowed HTTP methods as a list."""
        return [
            method.strip() for method in self.allow_methods_str.split(",") if method.strip()
        ]

    @property
    def allow_headers(self) -> List[str]:
        """Get allowed HTTP headers as a list."""
        return [
            header.strip() for header in self.allow_headers_str.split(",") if header.strip()
        ]


class PromptSettings(BaseSettings):
    """System prompt / persona configuration."""

    model_config = SettingsConfigDict(env_prefix="PROMPT_", case_sensitive=False)

    base_persona_prompt: str = Field(
        default="",
        description="Base system persona prompt (optional; falls back to built-in default if empty)",
    )
    tool_policy_prompt: str = Field(
        default="",
        description="Tool policy prompt appended when tools are enabled (optional; falls back to built-in default if empty)",
    )

    # Stored as a string to avoid JSON parsing issues; this is parsed by PromptService.
    firm_personas_json: str = Field(
        default="",
        description="JSON mapping of firm_id -> persona prompt string",
    )
    cache_ttl_seconds: int = Field(
        default=600,
        description="Redis cache TTL for firm personas (seconds)",
    )


class GRPCSettings(BaseSettings):
    """gRPC server configuration."""

    # Remove env_prefix to avoid conflicts - we'll use explicit aliases instead
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    grpc_enabled: bool = Field(
        default=True,
        description="Enable gRPC server. Env var: GRPC_ENABLED",
    )
    grpc_port: int = Field(
        default=50051,
        description="gRPC server port. Env var: GRPC_PORT",
    )
    grpc_max_workers: int = Field(
        default=10,
        description="Maximum number of worker threads for gRPC server. Env var: GRPC_MAX_WORKERS",
    )

    @property
    def enabled(self) -> bool:
        """Backward compatibility property."""
        return self.grpc_enabled

    @property
    def port(self) -> int:
        """Backward compatibility property."""
        return self.grpc_port

    @property
    def max_workers(self) -> int:
        """Backward compatibility property."""
        return self.grpc_max_workers


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(
        default="cognitive-orch", description="Application name. Env var: APP_NAME"
    )
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment. Env var: ENVIRONMENT",
    )
    debug: bool = Field(default=False, description="Enable debug mode. Env var: DEBUG")
    log_level: str = Field(
        default="INFO", description="Logging level. Env var: LOG_LEVEL"
    )

    # Internal API Key Authentication
    internal_api_key_enabled: bool = Field(
        default=False,
        description="Enable API-key auth for internal service endpoints. Env var: INTERNAL_API_KEY_ENABLED",
    )
    internal_api_key: Optional[str] = Field(
        default=None,
        description="Shared secret API key for internal services (sent as X-Internal-API-Key). Env var: INTERNAL_API_KEY",
    )

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    integration: IntegrationSettings = Field(default_factory=IntegrationSettings)
    context_window: ContextWindowSettings = Field(default_factory=ContextWindowSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    prompt: PromptSettings = Field(default_factory=PromptSettings)
    grpc: GRPCSettings = Field(default_factory=GRPCSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

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

    def validate_llm_configuration(self) -> None:
        """Validate that at least one LLM provider is configured."""
        if not any(
            [
                self.llm.has_azure_openai,
                self.llm.has_anthropic,
                self.llm.has_aws_bedrock,
                self.llm.has_groq,
            ]
        ):
            warnings.warn(
                "No LLM provider is configured. At least one provider (Azure OpenAI, "
                "Anthropic, AWS Bedrock, or Groq) must be configured.",
                UserWarning,
            )

    def validate_production_settings(self) -> None:
        """Validate that production settings are secure."""
        if self.is_production:
            if self.debug:
                raise ValueError("DEBUG must be False in production")

            # Validate LLM configuration
            if not any(
                [
                    self.llm.has_azure_openai,
                    self.llm.has_anthropic,
                    self.llm.has_aws_bedrock,
                    self.llm.has_groq,
                ]
            ):
                raise ValueError(
                    "At least one LLM provider must be configured in production. "
                    "Set AZURE_API_KEY/AZURE_API_BASE, ANTHROPIC_API_KEY, "
                    "AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_REGION, or GROQ_API_KEY."
                )

            # Validate internal API key if enabled
            if self.internal_api_key_enabled and not self.internal_api_key:
                raise ValueError(
                    "INTERNAL_API_KEY must be set when INTERNAL_API_KEY_ENABLED=true (internal endpoints protection)."
                )

            # Warn about missing API keys for configured models
            if self.llm.default_model_name.startswith("azure/") and not self.llm.has_azure_openai:
                warnings.warn(
                    f"Default model '{self.llm.default_model_name}' requires Azure OpenAI, "
                    "but AZURE_API_KEY or AZURE_API_BASE is not set.",
                    UserWarning,
                )

            if (
                self.llm.default_model_name.startswith("anthropic/")
                and not self.llm.has_anthropic
            ):
                warnings.warn(
                    f"Default model '{self.llm.default_model_name}' requires Anthropic, "
                    "but ANTHROPIC_API_KEY is not set.",
                    UserWarning,
                )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Validate LLM configuration
        _settings.validate_llm_configuration()
        # Validate production settings
        try:
            _settings.validate_production_settings()
        except ValueError as e:
            import logging

            logging.error(f"Configuration validation failed: {e}")
            if _settings.is_production:
                raise  # Fail fast in production
    return _settings


# Convenience function to get settings
settings = get_settings()

