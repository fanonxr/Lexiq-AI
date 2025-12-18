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

# Azure OpenAI Variables
variable "openai_sku_name" {
  description = "Azure OpenAI SKU name (S0 for dev, S1+ for prod)"
  type        = string
  default     = "S0"
}

variable "openai_public_network_access_enabled" {
  description = "Whether to enable public network access for Azure OpenAI"
  type        = bool
  default     = true
}

variable "openai_model_deployments" {
  description = "Map of Azure OpenAI model deployments. Key is deployment name, value contains model config."
  type = map(object({
    model_name    = string
    model_version = string
    scale_type    = string
    scale_capacity = number
    scale_tier    = optional(string) # One of: "Free", "Basic", "Standard", "Premium", "Enterprise"
    scale_size    = optional(string)
  }))
  default = {
    "gpt-4o" = {
      model_name    = "gpt-4o"
      model_version = "2024-08-06"  # Specific version required (2024-08-06 is the default)
      scale_type    = "Standard"
      scale_capacity = 1  # Start with 1 (minimum) - increase after quota approval
      scale_tier    = "Standard"  # Valid values: "Free", "Basic", "Standard", "Premium", "Enterprise"
      scale_size    = null
    }
  }
}

variable "openai_key_vault_enabled" {
  description = "Whether to store OpenAI secrets in Key Vault (requires Key Vault to exist)"
  type        = bool
  default     = true
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

# Entra ID Variables (for future use)
variable "entra_tenant_domain" {
  description = "Entra ID tenant domain (e.g., lexiqai.onmicrosoft.com)"
  type        = string
  default     = ""
}

variable "entra_app_client_id" {
  description = "Entra ID application client ID"
  type        = string
  default     = ""
  sensitive   = true
}

