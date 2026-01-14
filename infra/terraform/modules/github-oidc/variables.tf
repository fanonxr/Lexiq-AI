variable "project_name" {
  description = "Base name for all resources"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in format: owner/repo (e.g., 'your-org/lexiq-ai')"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to allow OIDC authentication for (e.g., 'main', 'develop'). Use '*' for all branches. DEPRECATED: Use github_environments instead."
  type        = string
  default     = ""
}

variable "github_environment" {
  description = "GitHub environment name for OIDC (optional). If set, restricts OIDC to this environment. DEPRECATED: Use github_environments instead."
  type        = string
  default     = ""
}

variable "github_environments" {
  description = "List of GitHub environments to create federated identity credentials for (e.g., ['dev', 'staging', 'prod']). If empty, will use github_branch or github_environment."
  type        = list(string)
  default     = []
}

variable "github_branches" {
  description = "List of GitHub branches to create federated identity credentials for (e.g., ['develop', 'staging', 'prod', 'master']). Used if github_environments is empty."
  type        = list(string)
  default     = []
}

variable "environment_resource_group_ids" {
  description = "Map of environment names to resource group IDs for role assignments (e.g., { dev = '...', staging = '...', prod = '...' })"
  type        = map(string)
  default     = {}
}

variable "container_registry_id" {
  description = "Resource ID of the Azure Container Registry"
  type        = string
}

variable "resource_group_id" {
  description = "Resource ID of the resource group"
  type        = string
}

variable "key_vault_id" {
  description = "Resource ID of the Key Vault (optional)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
