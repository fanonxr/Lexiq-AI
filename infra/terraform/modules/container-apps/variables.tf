variable "project_name" {
  description = "Base name for all resources"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "subnet_id" {
  description = "ID of the compute subnet for Container Apps Environment"
  type        = string
}

variable "managed_identity_id" {
  description = "Resource ID of the user-assigned managed identity"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "ID of the Log Analytics Workspace for Container Apps Environment"
  type        = string
}

variable "key_vault_id" {
  description = "ID of the Key Vault for secrets (optional - secrets can be configured manually)"
  type        = string
  default     = null
}

variable "key_vault_name" {
  description = "Name of the Key Vault (used to construct Key Vault URLs for Container Apps secrets)"
  type        = string
  default     = null
}

# Dependencies
variable "postgres_fqdn" {
  description = "FQDN of the PostgreSQL server"
  type        = string
}

variable "postgres_database_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "lexiqai"
}

variable "postgres_admin_username" {
  description = "PostgreSQL administrator username"
  type        = string
  default     = null
}

variable "managed_identity_name" {
  description = "Name of the Managed Identity (for database role grants)"
  type        = string
  default     = null
}

variable "storage_account_name" {
  description = "Name of the Azure Storage Account"
  type        = string
}

variable "storage_account_access_key" {
  description = "Primary access key for the Azure Storage Account (for Container Apps Environment storage)"
  type        = string
  sensitive   = true
}

# File Shares for persistent storage
variable "qdrant_file_share_name" {
  description = "Name of the Azure File Share for Qdrant persistent storage"
  type        = string
}

variable "rabbitmq_file_share_name" {
  description = "Name of the Azure File Share for RabbitMQ persistent storage"
  type        = string
}

# Container Registry Configuration
variable "container_registry" {
  description = "Container registry URL (e.g., 'myregistry.azurecr.io' or 'docker.io')"
  type        = string
  default     = "docker.io"
}

variable "image_tag" {
  description = "Container image tag (default: 'latest')"
  type        = string
  default     = "latest"
}

# Redis Configuration
variable "redis_password_secret_name" {
  description = "Name of the Key Vault secret containing Redis password"
  type        = string
  default     = "redis-password"
}

variable "redis_min_replicas" {
  description = "Minimum number of Redis replicas"
  type        = number
  default     = 0 # Scale to zero for cost savings
}

variable "redis_max_replicas" {
  description = "Maximum number of Redis replicas"
  type        = number
  default     = 1
}

variable "redis_cpu" {
  description = "CPU allocation for Redis container (0.25, 0.5, 0.75, 1.0, etc.)"
  type        = number
  default     = 0.5
}

variable "redis_memory" {
  description = "Memory allocation for Redis container (e.g., '0.5Gi', '1Gi')"
  type        = string
  default     = "1Gi"
}

variable "redis_image" {
  description = "Redis container image"
  type        = string
  default     = "redis:7-alpine"
}

# Application Insights
variable "application_insights_connection_string" {
  description = "Application Insights connection string (required for observability)"
  type        = string
}

# Custom Domains (optional - for production)
variable "api_core_custom_domain" {
  description = "Custom domain for API Core (e.g., 'api.example.com'). Leave empty to use default Container Apps FQDN."
  type        = string
  default     = ""
}

variable "voice_gateway_custom_domain" {
  description = "Custom domain for Voice Gateway (e.g., 'voice.example.com'). Leave empty to use default Container Apps FQDN."
  type        = string
  default     = ""
}

variable "integration_webhooks_custom_domain" {
  description = "Custom domain for Integration Worker Webhooks (e.g., 'webhooks.example.com'). Leave empty to use default Container Apps FQDN."
  type        = string
  default     = ""
}

variable "certificate_id" {
  description = "ID of the Container Apps managed certificate (for custom domains). Leave empty to use automatic Let's Encrypt certificates."
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
