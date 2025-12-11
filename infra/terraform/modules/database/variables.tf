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

variable "data_subnet_id" {
  description = "ID of the data subnet for PostgreSQL server"
  type        = string
}

variable "private_endpoint_subnet_id" {
  description = "ID of the private endpoint subnet"
  type        = string
}

variable "vnet_id" {
  description = "ID of the Virtual Network"
  type        = string
}

variable "database_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "lexiqai"
}

variable "admin_username" {
  description = "PostgreSQL administrator username"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16"
}

variable "sku_name" {
  description = "PostgreSQL SKU name (e.g., B_Standard_B1ms, GP_Standard_D2s_v3)"
  type        = string
}

variable "storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
}

# Note: Workload type is determined by the SKU selection:
# - B_Standard_* (Burstable) = DevTest workload (use for dev/staging)
# - GP_Standard_* (General Purpose) = GeneralPurpose workload (use for production)
# The workload_type parameter is not directly configurable in Terraform;
# it's automatically set based on the SKU tier.

variable "backup_retention_days" {
  description = "Backup retention in days"
  type        = number
  default     = 7
}

variable "geo_redundant_backup_enabled" {
  description = "Enable geo-redundant backups"
  type        = bool
  default     = false
}

variable "high_availability_enabled" {
  description = "Enable high availability (zone redundant)"
  type        = bool
  default     = false
}

variable "allow_azure_services" {
  description = "Allow access from Azure services (firewall rule)"
  type        = bool
  default     = false
}

variable "allow_compute_subnet_access" {
  description = "Allow direct access from compute subnet (for troubleshooting)"
  type        = bool
  default     = false
}

variable "compute_subnet_start_ip" {
  description = "Start IP address of compute subnet (for firewall rule)"
  type        = string
  default     = ""
}

variable "compute_subnet_end_ip" {
  description = "End IP address of compute subnet (for firewall rule)"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

