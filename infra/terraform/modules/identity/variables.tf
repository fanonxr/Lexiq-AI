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

variable "resource_group_id" {
  description = "ID of the resource group for role assignments"
  type        = string
  default     = null
}

variable "postgres_server_id" {
  description = "ID of the PostgreSQL server for role assignment"
  type        = string
  default     = null
}

variable "redis_cache_id" {
  description = "ID of the Redis cache for role assignment"
  type        = string
  default     = null
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

