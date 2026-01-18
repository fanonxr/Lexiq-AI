# Azure AD App Registration Module
# Manages Microsoft Entra ID (Azure AD) App Registration with all required configurations

terraform {
  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
  }
}

# Main App Registration
resource "azuread_application" "main" {
  display_name     = "${var.project_name}-app-${var.environment}"
  description      = "Azure AD App Registration for ${var.project_name} ${var.environment} environment"
  sign_in_audience = var.sign_in_audience # "AzureADMyOrg", "AzureADMultipleOrgs", "AzureADandPersonalMicrosoftAccount", "PersonalMicrosoftAccount"

  # Web redirect URIs (for OAuth flows)
  web {
    redirect_uris = var.web_redirect_uris
    implicit_grant {
      access_token_issuance_enabled = false
      id_token_issuance_enabled     = true # Required for OIDC
    }
  }

  # Single-page application (SPA) redirect URIs (for frontend)
  single_page_application {
    redirect_uris = var.spa_redirect_uris
  }

  # Optional: Public client (mobile/desktop apps)
  # Not needed for web apps, but can be enabled if required
  # public_client {
  #   redirect_uris = var.public_client_redirect_uris
  # }

  # API configuration - Expose an API
  # This allows the frontend to request tokens for the backend API
  # Only create api block if we have exposed scopes
  dynamic "api" {
    for_each = length(var.exposed_api_scopes) > 0 ? [1] : []
    content {
      mapped_claims_enabled = false

      # OAuth2 permission scopes (exposed API scopes)
      dynamic "oauth2_permission_scope" {
        for_each = var.exposed_api_scopes
        content {
          id                         = oauth2_permission_scope.value.id
          admin_consent_display_name = oauth2_permission_scope.value.admin_consent_display_name
          admin_consent_description  = oauth2_permission_scope.value.admin_consent_description
          user_consent_display_name  = oauth2_permission_scope.value.user_consent_display_name
          user_consent_description   = oauth2_permission_scope.value.user_consent_description
          value                      = oauth2_permission_scope.value.value
          type                       = oauth2_permission_scope.value.type # "User" or "Admin"
          enabled                    = oauth2_permission_scope.value.enabled
        }
      }
    }
  }

  # Set Application ID URI (Identifier URIs)
  # This is used for the exposed API (e.g., api://<client-id> or api://<custom-domain>)
  # If not provided, Azure AD will auto-generate api://<client-id>
  # Note: identifier_uris is a set, so we use toset()
  identifier_uris = var.api_application_id_uri != "" ? toset([var.api_application_id_uri]) : []

  # Required resource access (API permissions)
  # Microsoft Graph API permissions
  required_resource_access {
    resource_app_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph

    dynamic "resource_access" {
      for_each = var.microsoft_graph_permissions
      content {
        id   = resource_access.value.id   # Permission ID
        type = resource_access.value.type # "Role" (application permission) or "Scope" (delegated permission)
      }
    }
  }

  # Optional: Additional required resource access
  dynamic "required_resource_access" {
    for_each = var.additional_resource_access
    content {
      resource_app_id = required_resource_access.value.resource_app_id

      dynamic "resource_access" {
        for_each = required_resource_access.value.resource_access
        content {
          id   = resource_access.value.id
          type = resource_access.value.type
        }
      }
    }
  }

  # Optional: App roles (for RBAC)
  dynamic "app_role" {
    for_each = var.app_roles
    content {
      id                   = app_role.value.id
      allowed_member_types = app_role.value.allowed_member_types
      description          = app_role.value.description
      display_name         = app_role.value.display_name
      enabled              = app_role.value.enabled
      value                = app_role.value.value
    }
  }

  # Optional: Tags (convert map to set of strings)
  tags = length(var.tags) > 0 ? [for k, v in var.tags : "${k}=${v}"] : []
}

# Service Principal (required for the app registration to be used)
resource "azuread_service_principal" "main" {
  client_id                    = azuread_application.main.client_id
  app_role_assignment_required = var.app_role_assignment_required
  description                  = "Service principal for ${var.project_name} ${var.environment}"
  tags                         = length(var.tags) > 0 ? [for k, v in var.tags : "${k}=${v}"] : []
}

# Optional: Client Secret (if password authentication is needed)
# Note: For production, consider using certificates instead
resource "azuread_application_password" "main" {
  count          = var.create_client_secret ? 1 : 0
  application_id = azuread_application.main.id
  display_name   = "${var.project_name}-secret-${var.environment}"

  # Optional: Set expiration
  end_date = var.client_secret_expiration != "" ? var.client_secret_expiration : null

  # Rotate secret if it already exists
  rotate_when_changed = {
    rotation = timestamp()
  }
}

# Store client secret in Key Vault (if Key Vault is provided)
resource "azurerm_key_vault_secret" "client_secret" {
  count = var.create_client_secret && var.key_vault_id != null ? 1 : 0

  name         = "azure-ad-b2c-client-secret"
  value        = azuread_application_password.main[0].value
  key_vault_id = var.key_vault_id

  content_type = "azure-ad-client-secret"

  tags = merge(
    var.tags,
    {
      SecretType = "azure-ad"
      ManagedBy  = "Terraform"
    }
  )

  depends_on = [azuread_application_password.main]
}

# Note: Admin consent for API permissions must be granted manually in Azure Portal
# or via Azure CLI/PowerShell. Terraform cannot grant admin consent automatically
# due to Azure AD security restrictions.
#
# To grant admin consent manually:
# 1. Go to Azure Portal → Azure Active Directory → App registrations
# 2. Select your app → API permissions
# 3. Click "Grant admin consent for [Your Organization]"
#
# Or via Azure CLI:
# az ad app permission admin-consent --id <application-id>
