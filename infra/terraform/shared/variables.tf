variable "project_name" {
  description = "Base name for all resources (e.g., 'lexiqai')"
  type        = string
  default     = "lexiqai"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "dns_zone_name" {
  description = "DNS zone name (e.g., 'lexiqai.com'). Leave empty if using external DNS."
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository in format: owner/repo (e.g., 'fanonxr/Lexiq-AI')"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to allow OIDC authentication for. Use '*' for all branches. DEPRECATED: Use github_environments instead."
  type        = string
  default     = ""
}

variable "github_environments" {
  description = "List of GitHub environments to create federated identity credentials for (e.g., ['dev', 'staging', 'prod']). These should match your GitHub Actions workflow environments. Only include environments that have been created."
  type        = list(string)
  default     = ["dev"] # Start with dev, add staging and prod as you create them
}

variable "environment_resource_group_names" {
  description = "Map of environment names to resource group names for role assignments (e.g., { dev = 'lexiqai-rg-dev', staging = 'lexiqai-rg-staging', prod = 'lexiqai-rg-prod' }). Only include resource groups that exist."
  type        = map(string)
  default = {
    dev = "lexiqai-rg-dev"
    # Add staging and prod as you create those environments:
    # staging = "lexiqai-rg-staging"
    # prod    = "lexiqai-rg-prod"
  }
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "LexiqAI"
    ManagedBy   = "Terraform"
    Environment = "shared"
    CostCenter  = "Engineering"
  }
}
