variable "project_name" {
  description = "Base name for the resource"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "location" {
  description = "Azure region for the resource"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "sku_name" {
  description = "SKU name for the Cognitive Services account (e.g., S0, S1)"
  type        = string
  default     = "S0"
}

variable "public_network_access_enabled" {
  description = "Whether public network access is enabled"
  type        = bool
  default     = true
}

variable "custom_subdomain_name" {
  description = "Custom subdomain name for the Cognitive Services account (optional)"
  type        = string
  default     = null
}

variable "model_deployments" {
  description = "Map of model deployments to create. Key is deployment name, value contains model config."
  type = map(object({
    model_name    = string      # e.g., "gpt-4o", "gpt-4-turbo"
    model_version = string      # e.g., "0613", "latest"
    scale_type    = string      # "Standard" or "Manual"
    scale_capacity = number      # Capacity units
    scale_tier    = optional(string) # One of: "Free", "Basic", "Standard", "Premium", "Enterprise"
    scale_size    = optional(string) # e.g., "1", "2"
  }))
  default = {
    "gpt-4o" = {
      model_name    = "gpt-4o"
      model_version = "2024-08-06"  # Specific version required (2024-08-06 is the default)
      scale_type    = "Standard"
      scale_capacity = 10
      scale_tier    = "Standard"
      scale_size    = null
    }
  }
}

variable "rai_policy_name" {
  description = "Responsible AI policy name (optional)"
  type        = string
  default     = null
}

variable "key_vault_id" {
  description = "ID of the Key Vault to store secrets (required if store_secrets_in_key_vault is true)."
  type        = string
  default     = null
}

variable "store_secrets_in_key_vault" {
  description = "Whether to store OpenAI secrets in Key Vault. If true, key_vault_id must be provided."
  type        = bool
  default     = false
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

