# Azure AD App Registration Variables

variable "azure_ad_sign_in_audience" {
  description = "The Microsoft account types that are supported. Options: AzureADMyOrg, AzureADMultipleOrgs, AzureADandPersonalMicrosoftAccount, PersonalMicrosoftAccount"
  type        = string
  default     = "AzureADMyOrg"
}

variable "azure_ad_web_redirect_uris" {
  description = "Web redirect URIs for server-side OAuth flows (e.g., API callback URLs)"
  type        = list(string)
  default     = []
}

variable "azure_ad_spa_redirect_uris" {
  description = "Single-page application (SPA) redirect URIs for frontend OAuth flows"
  type        = list(string)
  default     = []
}

variable "azure_ad_api_application_id_uri" {
  description = "Application ID URI for the exposed API (e.g., api://<client-id> or api://<custom-domain>). If empty, defaults to api://<client-id>"
  type        = string
  default     = ""
}

variable "azure_ad_exposed_api_scopes" {
  description = "OAuth2 permission scopes to expose for the API (for frontend to request tokens). The 'id' field must be a valid UUID."
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
  default = [
    {
      id                         = "00000000-0000-0000-0000-000000000001" # Must be a valid UUID
      admin_consent_display_name = "Access API"
      admin_consent_description  = "Allow the application to access the API on behalf of the signed-in user"
      user_consent_display_name  = "Access API"
      user_consent_description   = "Allow the application to access the API on your behalf"
      value                      = "api.access"
      type                       = "User"
      enabled                    = true
    }
  ]
}

variable "azure_ad_microsoft_graph_permissions" {
  description = "Microsoft Graph API permissions (delegated or application)"
  type = list(object({
    id   = string # Permission ID
    type = string # "Role" (application permission) or "Scope" (delegated permission)
  }))
  default = [
    # Delegated permissions (user context)
    {
      id   = "e1fe6dd8-ba31-4d61-89e7-88639da4683d" # User.Read
      type = "Scope"
    },
    {
      id   = "37f7f235-527c-4136-accd-4a02d197296e" # Calendars.ReadWrite
      type = "Scope"
    },
    {
      id   = "df021288-bdef-4463-88db-98f22de89214" # offline_access (for refresh tokens)
      type = "Scope"
    }
  ]
}

variable "azure_ad_additional_resource_access" {
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

variable "azure_ad_app_roles" {
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

variable "azure_ad_create_client_secret" {
  description = "Whether to create a client secret (password) for the application"
  type        = bool
  default     = true
}

variable "azure_ad_client_secret_expiration" {
  description = "Expiration date for client secret (RFC3339 format, e.g., '2025-12-31T23:59:59Z'). If empty, secret doesn't expire."
  type        = string
  default     = ""
}

variable "azure_ad_app_role_assignment_required" {
  description = "Whether the service principal requires an app role assignment"
  type        = bool
  default     = false
}

variable "azure_ad_grant_admin_consent" {
  description = "Whether to grant admin consent for application permissions (requires appropriate Azure AD permissions)"
  type        = bool
  default     = false
}
