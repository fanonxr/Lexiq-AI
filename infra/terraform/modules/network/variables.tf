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

variable "vnet_address_space" {
  description = "Address space for the Virtual Network"
  type        = list(string)
}

variable "compute_subnet_cidr" {
  description = "CIDR block for compute subnet"
  type        = string
}

variable "data_subnet_cidr" {
  description = "CIDR block for data subnet"
  type        = string
}

variable "private_endpoint_subnet_cidr" {
  description = "CIDR block for private endpoint subnet"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

