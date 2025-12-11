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

variable "private_endpoint_subnet_id" {
  description = "ID of the subnet for Redis private endpoint"
  type        = string
}

variable "vnet_id" {
  description = "ID of the Virtual Network for DNS zone linking"
  type        = string
}

variable "sku_name" {
  description = "Redis SKU name (Basic or Standard)"
  type        = string
  default     = "Basic"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.sku_name)
    error_message = "SKU name must be Basic, Standard, or Premium."
  }
}

variable "family" {
  description = "Redis SKU family (C for Basic/Standard)"
  type        = string
  default     = "C"
  validation {
    condition     = contains(["C", "P"], var.family)
    error_message = "Family must be C (for Basic/Standard) or P (for Premium)."
  }
}

variable "capacity" {
  description = "Redis capacity (0 for C0, 1 for C1, etc.)"
  type        = number
  default     = 0
}

variable "redis_version" {
  description = "Redis version (4 or 6 - Azure Redis Cache supports versions 4 and 6)"
  type        = string
  default     = "6"
  validation {
    condition     = contains(["4", "6"], var.redis_version)
    error_message = "Redis version must be 4 or 6 (Azure Redis Cache supported versions)."
  }
}

variable "enable_non_ssl_port" {
  description = "Enable non-SSL port (for local dev compatibility)"
  type        = bool
  default     = false
}

variable "rdb_backup_enabled" {
  description = "Enable RDB backup persistence"
  type        = bool
  default     = false
}

variable "rdb_backup_frequency" {
  description = "RDB backup frequency (only used if rdb_backup_enabled is true)"
  type        = number
  default     = null
}

variable "rdb_backup_max_snapshot_count" {
  description = "Maximum number of RDB snapshots (only used if rdb_backup_enabled is true)"
  type        = number
  default     = null
}

variable "rdb_storage_connection_string" {
  description = "Storage account connection string for RDB backups (only used if rdb_backup_enabled is true)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

