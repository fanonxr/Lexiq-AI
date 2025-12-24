"""Configuration management using pydantic-settings."""

import warnings
from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class RabbitMQSettings(BaseSettings):
    """RabbitMQ message queue configuration."""

    model_config = SettingsConfigDict(env_prefix="RABBITMQ_", case_sensitive=False)

    url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ connection URL",
    )
    queue_name: str = Field(
        default="document-ingestion",
        description="Queue name for ingestion jobs. Env var: RABBITMQ_queue_name",
    )
    exchange_name: str = Field(
        default="document-ingestion-exchange",
        description="Exchange name for routing. Env var: RABBITMQ_exchange_name",
    )
    dead_letter_queue_name: str = Field(
        default="document-ingestion-dlq",
        description="Dead-letter queue name for failed jobs. Env var: RABBITMQ_dead_letter_queue_name",
    )
    routing_key: str = Field(
        default="document.ingestion",
        description="Routing key for messages. Env var: RABBITMQ_routing_key",
    )
    prefetch_count: int = Field(
        default=10,
        description="Number of unacknowledged messages per worker. Env var: RABBITMQ_prefetch_count",
    )
    queue_durable: bool = Field(
        default=True, description="Make queue durable. Env var: RABBITMQ_queue_durable"
    )
    message_ttl: Optional[int] = Field(
        default=None,
        description="Message TTL in milliseconds (None = no TTL). Env var: RABBITMQ_message_ttl",
    )


class StorageSettings(BaseSettings):
    """Azure Blob Storage configuration."""

    model_config = SettingsConfigDict(env_prefix="STORAGE_", case_sensitive=False)

    account_name: Optional[str] = Field(
        default=None, description="Azure Storage Account name"
    )
    account_key: Optional[str] = Field(
        default=None, description="Azure Storage Account key (use Managed Identity instead)"
    )
    connection_string: Optional[str] = Field(
        default=None,
        description="Azure Storage connection string (use Managed Identity instead)",
    )
    use_managed_identity: bool = Field(
        default=True,
        description="Use Managed Identity for authentication (recommended)",
    )

    @property
    def is_configured(self) -> bool:
        """Check if storage is configured."""
        return bool(self.account_name) and (
            bool(self.connection_string) or bool(self.account_key) or self.use_managed_identity
        )


class EmbeddingProvider(str, Enum):
    """Embedding provider selection."""

    OPENAI = "openai"
    AZURE = "azure"


class EmbeddingSettings(BaseSettings):
    """Embedding configuration (provider-agnostic)."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    embedding_provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OPENAI,
        description="Embedding provider: openai or azure. Env var: EMBEDDING_PROVIDER",
    )

    # OpenAI (direct) embeddings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (direct) for embeddings. Env var: OPENAI_API_KEY",
    )
    # Optional alternate env var name some users use
    open_ai_api_key: Optional[str] = Field(
        default=None,
        description="Alternate OpenAI API key env var name. Env var: OPEN_AI_API_KEY",
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Optional OpenAI base URL (advanced). Env var: OPENAI_BASE_URL",
    )
    open_ai_base_url: Optional[str] = Field(
        default=None,
        description="Alternate OpenAI base URL env var name. Env var: OPEN_AI_BASE_URL",
    )

    # Azure OpenAI embeddings (optional)
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Azure OpenAI endpoint URL. Env var: AZURE_OPENAI_ENDPOINT"
    )
    azure_openai_api_key: Optional[str] = Field(
        default=None, description="Azure OpenAI API key. Env var: AZURE_OPENAI_API_KEY"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version. Env var: AZURE_OPENAI_API_VERSION",
    )

    # Model configuration
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name (OpenAI direct). Env var: EMBEDDING_MODEL",
    )
    embedding_deployment_name: Optional[str] = Field(
        default=None,
        description="Embedding deployment name (Azure OpenAI). Env var: EMBEDDING_DEPLOYMENT_NAME",
    )
    embedding_dimension: Optional[int] = Field(
        default=None,
        description="Optional embedding dimension (used for validation / Qdrant collection sizing). Env var: EMBEDDING_DIMENSION",
    )
    embedding_batch_size: int = Field(
        default=100,
        description="Batch size for embedding generation. Env var: EMBEDDING_BATCH_SIZE",
    )
    embedding_timeout: float = Field(
        default=30.0,
        description="Embedding request timeout in seconds. Env var: EMBEDDING_TIMEOUT",
    )
    embedding_max_retries: int = Field(
        default=5,
        description="Max retries for embedding requests. Env var: EMBEDDING_MAX_RETRIES",
    )

    @model_validator(mode="after")
    def normalize_openai_env_vars(self) -> "EmbeddingSettings":
        """Accept OPEN_AI_* as aliases for OPENAI_* for convenience."""
        if not self.openai_api_key and self.open_ai_api_key:
            self.openai_api_key = self.open_ai_api_key
        if not self.openai_base_url and self.open_ai_base_url:
            self.openai_base_url = self.open_ai_base_url
        return self

    @property
    def provider(self) -> EmbeddingProvider:
        """Get the embedding provider (backward compatibility)."""
        return self.embedding_provider

    @property
    def is_configured(self) -> bool:
        """Check if the selected embedding provider is configured."""
        if self.embedding_provider == EmbeddingProvider.OPENAI:
            return bool(self.openai_api_key)
        if self.embedding_provider == EmbeddingProvider.AZURE:
            return bool(self.azure_openai_endpoint and self.azure_openai_api_key and self.embedding_deployment_name)
        return False

    @property
    def resolved_model_name(self) -> str:
        """Get the effective model/deployment name to use for embeddings."""
        if self.embedding_provider == EmbeddingProvider.AZURE:
            return self.embedding_deployment_name or ""
        return self.embedding_model

    @property
    def batch_size(self) -> int:
        """Get batch size (backward compatibility)."""
        return self.embedding_batch_size

    @property
    def timeout(self) -> float:
        """Get timeout (backward compatibility)."""
        return self.embedding_timeout

    @property
    def max_retries(self) -> int:
        """Get max retries (backward compatibility)."""
        return self.embedding_max_retries


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
    collection_prefix: str = Field(
        default="firm_",
        description="Prefix for collection names (firm_{firm_id}). Env var: QDRANT_collection_prefix",
    )

    @property
    def is_cloud(self) -> bool:
        """Check if using Qdrant Cloud (has API key)."""
        return bool(self.api_key)


class ChunkingSettings(BaseSettings):
    """Text chunking configuration."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    chunk_size: int = Field(
        default=1000, description="Chunk size in tokens. Env var: CHUNK_SIZE"
    )
    chunk_overlap: int = Field(
        default=200, description="Overlap between chunks in tokens. Env var: CHUNK_OVERLAP"
    )
    chunking_method: str = Field(
        default="sentence",
        description="Chunking method: sentence, paragraph, or fixed. Env var: CHUNKING_METHOD",
    )

    @field_validator("chunking_method")
    @classmethod
    def validate_chunking_method(cls, v: str) -> str:
        """Validate chunking method."""
        valid_methods = ["sentence", "paragraph", "fixed"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Chunking method must be one of {valid_methods}")
        return v.lower()


class RetrySettings(BaseSettings):
    """Retry configuration for failed operations."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    max_retries: int = Field(
        default=3, description="Maximum number of retries. Env var: MAX_RETRIES"
    )
    backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff factor. Env var: RETRY_BACKOFF_FACTOR",
    )
    max_delay: int = Field(
        default=300, description="Maximum delay between retries in seconds. Env var: RETRY_MAX_DELAY"
    )


class APICoreSettings(BaseSettings):
    """API Core service configuration."""

    model_config = SettingsConfigDict(env_prefix="CORE_API_", case_sensitive=False)

    url: str = Field(
        default="http://localhost:8000",
        description="Core API service URL. Env var: CORE_API_url",
    )
    timeout: int = Field(
        default=30, description="Request timeout in seconds. Env var: CORE_API_timeout"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Internal API key for calling API Core internal endpoints (sent as X-Internal-API-Key). Env var: CORE_API_api_key",
    )


class ServerSettings(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    host: str = Field(default="0.0.0.0", description="Server host. Env var: HOST")
    port: int = Field(default=8003, description="HTTP server port. Env var: PORT")
    reload: bool = Field(
        default=False, description="Enable auto-reload (development only). Env var: RELOAD"
    )


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
        default="document-ingestion", description="Application name. Env var: APP_NAME"
    )
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment. Env var: ENVIRONMENT",
    )
    debug: bool = Field(default=False, description="Enable debug mode. Env var: DEBUG")
    log_level: str = Field(
        default="INFO", description="Logging level. Env var: LOG_LEVEL"
    )

    # Supported file types (stored as string, parsed to list)
    allowed_file_types_str: Optional[str] = Field(
        default="pdf,docx,txt,md",
        description="Allowed file types for processing (comma-separated). Env var: ALLOWED_FILE_TYPES",
    )

    # Sub-settings
    rabbitmq: Optional[RabbitMQSettings] = None
    storage: Optional[StorageSettings] = None
    embedding: Optional[EmbeddingSettings] = None
    qdrant: Optional[QdrantSettings] = None
    chunking: Optional[ChunkingSettings] = None
    retry: Optional[RetrySettings] = None
    api_core: Optional[APICoreSettings] = None
    server: Optional[ServerSettings] = None

    @model_validator(mode="after")
    def initialize_nested_settings(self) -> "Settings":
        """Initialize nested settings to ensure they read from environment."""
        if self.rabbitmq is None:
            self.rabbitmq = RabbitMQSettings()
        if self.storage is None:
            self.storage = StorageSettings()
        if self.embedding is None:
            self.embedding = EmbeddingSettings()
        if self.qdrant is None:
            self.qdrant = QdrantSettings()
        if self.chunking is None:
            self.chunking = ChunkingSettings()
        if self.retry is None:
            self.retry = RetrySettings()
        if self.api_core is None:
            self.api_core = APICoreSettings()
        if self.server is None:
            self.server = ServerSettings()
        return self

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
    def allowed_file_types(self) -> List[str]:
        """Get allowed file types as a list."""
        if not self.allowed_file_types_str:
            return ["pdf", "docx", "txt", "md"]
        return [
            ft.strip().lower()
            for ft in self.allowed_file_types_str.split(",")
            if ft.strip()
        ]

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

    def validate_configuration(self) -> None:
        """Validate that required services are configured."""
        if not self.storage.is_configured:
            warnings.warn(
                "Azure Blob Storage is not configured. Set STORAGE_ACCOUNT_NAME and "
                "either STORAGE_USE_MANAGED_IDENTITY=true or STORAGE_CONNECTION_STRING",
                UserWarning,
            )

        if not self.embedding.is_configured:
            warnings.warn(
                "Embeddings are not configured. For OpenAI direct set EMBEDDING_PROVIDER=openai and OPENAI_API_KEY. "
                "For Azure set EMBEDDING_PROVIDER=azure and AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/"
                "EMBEDDING_DEPLOYMENT_NAME.",
                UserWarning,
            )

    def validate_production_settings(self) -> None:
        """Validate that production settings are secure."""
        if self.is_production:
            if self.debug:
                raise ValueError("DEBUG must be False in production")

            if not self.storage.is_configured:
                raise ValueError(
                    "Azure Blob Storage must be configured in production. "
                    "Set STORAGE_ACCOUNT_NAME and STORAGE_USE_MANAGED_IDENTITY=true"
                )

            if not self.embedding.is_configured:
                raise ValueError(
                    "Embeddings must be configured in production. "
                    "For OpenAI direct set EMBEDDING_PROVIDER=openai and OPENAI_API_KEY. "
                    "For Azure set EMBEDDING_PROVIDER=azure and AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/"
                    "EMBEDDING_DEPLOYMENT_NAME."
                )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Validate configuration
        _settings.validate_configuration()
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

