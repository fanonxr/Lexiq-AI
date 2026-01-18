variable "project_name" {
  description = "Base name for the application"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "sign_in_audience" {
  description = "The Microsoft account types that are supported for the current application. Options: AzureADMyOrg, AzureADMultipleOrgs, AzureADandPersonalMicrosoftAccount, PersonalMicrosoftAccount"
  type        = string
  default     = "AzureADMyOrg"
}

# Redirect URIs
variable "web_redirect_uris" {
  description = "Web redirect URIs for OAuth flows (e.g., https://app.example.com/auth/callback)"
  type        = list(string)
  default     = []
}

variable "spa_redirect_uris" {
  description = "Single-page application (SPA) redirect URIs for frontend OAuth flows"
  type        = list(string)
  default     = []
}

variable "public_client_redirect_uris" {
  description = "Public client redirect URIs (for mobile/desktop apps)"
  type        = list(string)
  default     = []
}

# API Configuration
variable "api_application_id_uri" {
  description = "Application ID URI for the exposed API (e.g., api://<client-id> or api://<custom-domain>). If empty, defaults to api://<client-id>"
  type        = string
  default     = ""
}

variable "exposed_api_scopes" {
  description = "OAuth2 permission scopes to expose for the API"
  type = list(object({
    id                         = string
    admin_consent_display_name = string
    admin_consent_description  = string
    user_consent_display_name  = string
    user_consent_description   = string
    value                      = string
    type                       = string # "User" or "Admin"
    enabled                    = bool
  }))
  default = []
}

# Microsoft Graph API Permissions
variable "microsoft_graph_permissions" {
  description = "Microsoft Graph API permissions (delegated or application)"
  type = list(object({
    id   = string # Permission ID (e.g., "e1fe6dd8-ba31-4d61-89e7-88639da4683d" for User.Read)
    type = string # "Role" (application permission) or "Scope" (delegated permission)
  }))
  default = []
}

# Additional Resource Access
variable "additional_resource_access" {
  description = "Additional required resource access (APIs other than Microsoft Graph)"
  type = list(object({
    resource_app_id = string
    resource_access = list(object({
      id   = string
      type = string
    }))
  }))
  default = []
}

# App Roles (for RBAC)
variable "app_roles" {
  description = "App roles for role-based access control"
  type = list(object({
    id                   = string
    allowed_member_types = list(string) # ["User", "Application"]
    description          = string
    display_name         = string
    enabled              = bool
    value                = string
  }))
  default = []
}

# Client Secret
variable "create_client_secret" {
  description = "Whether to create a client secret (password) for the application"
  type        = bool
  default     = true
}

variable "client_secret_expiration" {
  description = "Expiration date for client secret (RFC3339 format, e.g., '2025-12-31T23:59:59Z'). If empty, secret doesn't expire."
  type        = string
  default     = ""
}

# Key Vault Integration
variable "key_vault_id" {
  description = "Azure Key Vault ID to store the client secret (optional)"
  type        = string
  default     = null
}

# Service Principal
variable "app_role_assignment_required" {
  description = "Whether this service principal requires an app role assignment"
  type        = bool
  default     = false
}

# Admin Consent
variable "grant_admin_consent" {
  description = "Whether to grant admin consent for application permissions (requires appropriate Azure AD permissions)"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
