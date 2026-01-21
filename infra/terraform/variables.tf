variable "project_name" {
  description = "Base name for all resources (e.g., 'lexiqai')"
  type        = string
  default     = "lexiqai"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "LexiqAI"
    ManagedBy   = "Terraform"
    Environment = "" # Will be set from var.environment
  }
}

# Network Variables
variable "vnet_address_space" {
  description = "Address space for the Virtual Network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "compute_subnet_cidr" {
  description = "CIDR block for compute subnet (Container Apps)"
  type        = string
  default     = "10.0.1.0/24"
}

variable "data_subnet_cidr" {
  description = "CIDR block for data subnet (Databases)"
  type        = string
  default     = "10.0.2.0/24"
}

variable "private_endpoint_subnet_cidr" {
  description = "CIDR block for private endpoint subnet"
  type        = string
  default     = "10.0.3.0/24"
}

# Database Variables
variable "postgres_admin_username" {
  description = "PostgreSQL administrator username"
  type        = string
  sensitive   = true
  default     = "lexiqai_admin"
}

variable "postgres_admin_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}

variable "postgres_sku_name" {
  description = "PostgreSQL SKU name (e.g., B_Standard_B1ms for dev, GP_Standard_D2s_v3 for prod)"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
  default     = 32768 # 32 GB
}

variable "grant_postgres_database_roles" {
  description = "Automatically grant database roles to Managed Identity via Terraform (requires psql). If false, run scripts/grant-postgres-database-roles.sh manually. Recommended: true for production, false for development"
  type        = bool
  default     = true # Default to true for automatic setup
}

variable "postgres_backup_retention_days" {
  description = "PostgreSQL backup retention in days"
  type        = number
  default     = 7
}

# Note: PostgreSQL workload type is determined by the SKU:
# - B_Standard_* (Burstable) = DevTest workload (use for dev/staging)
# - GP_Standard_* (General Purpose) = GeneralPurpose workload (use for production)
# The workload_type is not a direct Terraform parameter; it's set automatically based on SKU tier.

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16"
}

# Redis Variables
variable "redis_sku_name" {
  description = "Redis SKU name (e.g., Basic for dev, Standard for prod)"
  type        = string
  default     = "Basic"
}

variable "redis_family" {
  description = "Redis SKU family (C for Basic/Standard)"
  type        = string
  default     = "C"
}

variable "redis_capacity" {
  description = "Redis capacity (0 for Basic C0, 1 for Standard C1, etc.)"
  type        = number
  default     = 0
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7.0"
}

# Container Registry Variables
variable "container_image_tag" {
  description = "Container image tag/version for all services (e.g., 'v1.0.0', 'latest', 'main-abc123'). Should be updated for each build."
  type        = string
  default     = "latest"
}

# DNS & Custom Domain Variables (optional)
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

# Optional: Azure DNS Zone (if managing DNS through Azure)
variable "dns_zone_name" {
  description = "Azure DNS zone name (e.g., 'lexiqai.com'). Leave empty if using external DNS provider."
  type        = string
  default     = ""
}

# Static Web Apps Variables
variable "static_web_app_custom_domain" {
  description = "Custom domain for Static Web App (e.g., 'www.lexiqai.com' or 'app.lexiqai.com'). Leave empty to use default Static Web Apps domain."
  type        = string
  default     = ""
}

variable "static_web_app_location" {
  description = "Azure region for Static Web Apps (must be a supported Static Web Apps region, e.g., 'East US 2')"
  type        = string
  default     = "EastUS2" # Static Web Apps specific location
}

# Storage Account Variables
variable "storage_account_tier" {
  description = "Storage account tier (Standard or Premium)"
  type        = string
  default     = "Standard"
}

variable "storage_account_replication_type" {
  description = "Storage account replication type (LRS for dev, GRS/ZRS for prod)"
  type        = string
  default     = "LRS"
}

variable "storage_public_network_access_enabled" {
  description = "Whether public network access is enabled for storage account"
  type        = bool
  default     = true
}

variable "storage_blob_soft_delete_retention_days" {
  description = "Number of days to retain soft-deleted blobs"
  type        = number
  default     = 7
}

variable "storage_container_soft_delete_retention_days" {
  description = "Number of days to retain soft-deleted containers"
  type        = number
  default     = 7
}

# Container Apps Variables (for future use)
variable "container_apps_environment_name" {
  description = "Name for Container Apps Environment"
  type        = string
  default     = ""
}

# Entra ID Variables (for Static Web App and application configuration)
variable "entra_tenant_domain" {
  description = "Entra ID tenant domain (e.g., lexiqai.onmicrosoft.com)"
  type        = string
  default     = ""
}

variable "entra_app_client_id" {
  description = "Entra ID application client ID (for frontend authentication)"
  type        = string
  default     = ""
  sensitive   = false # Client ID is safe to be public in OAuth flows
}

variable "entra_authority" {
  description = "Entra ID authority URL (default: https://login.microsoftonline.com/common, or use tenant-specific URL)"
  type        = string
  default     = "https://login.microsoftonline.com/common"
}

# GitHub OIDC Variables (for CI/CD)
variable "github_repository" {
  description = "GitHub repository in format: owner/repo (e.g., 'your-org/lexiq-ai'). Leave empty to disable GitHub OIDC setup."
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "GitHub branch to allow OIDC authentication for (e.g., 'main', 'develop', 'master'). Used for GitHub Actions OIDC federation."
  type        = string
  default     = "main"
}
