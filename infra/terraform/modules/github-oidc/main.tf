# GitHub OIDC Federation for Azure Authentication
# This allows GitHub Actions to authenticate to Azure without storing secrets

# Azure AD Application for GitHub OIDC
resource "azuread_application" "github_actions" {
  display_name = "${var.project_name}-github-actions-${var.environment}"
  description  = "GitHub Actions OIDC federation for ${var.project_name} ${var.environment}"

  # Optional: API access if needed
  sign_in_audience = "AzureADMyOrg"

  tags = [for k, v in var.tags : "${k}=${v}"]
}

# Service Principal for GitHub Actions
resource "azuread_service_principal" "github_actions" {
  client_id                    = azuread_application.github_actions.client_id
  app_role_assignment_required = false

  tags = [for k, v in var.tags : "${k}=${v}"]

  depends_on = [azuread_application.github_actions]
}

# Federated Identity Credentials for GitHub Environments (Recommended)
# Create credentials for each GitHub environment (dev, staging, prod)
# This matches the GitHub Actions workflow which uses environment: dev, staging, prod
# This is more secure than branch-based auth as it uses GitHub's environment protection features
resource "azuread_application_federated_identity_credential" "github_actions_environments" {
  for_each = length(var.github_environments) > 0 ? toset(var.github_environments) : toset([])

  # Reference the application's object_id (not client_id)
  # The Azure AD provider expects the object_id in the format: /applications/{object_id}
  application_id = "/applications/${azuread_application.github_actions.object_id}"
  display_name   = "${var.project_name}-github-actions-${each.value}"
  description    = "Federated identity for GitHub Actions (${each.value} environment)"

  # GitHub repository in format: owner/repo
  audiences = ["api://AzureADTokenExchange"]
  issuer    = "https://token.actions.githubusercontent.com"

  # Use GitHub environment format: repo:owner/repo:environment:env-name
  # This matches the GitHub Actions workflow environment configuration
  subject = "repo:${var.github_repository}:environment:${each.value}"

  # Ensure the application and service principal are created before the federated identity credential
  depends_on = [
    azuread_application.github_actions,
    azuread_service_principal.github_actions
  ]
}

# Federated Identity Credentials for GitHub Branches (Alternative to environments)
# Create credentials for each branch (develop, staging, prod, master)
# Use this if you prefer branch-based authentication instead of environment-based
resource "azuread_application_federated_identity_credential" "github_actions_branches" {
  for_each = length(var.github_branches) > 0 ? toset(var.github_branches) : toset([])

  # Reference the application's object_id (not client_id)
  application_id = "/applications/${azuread_application.github_actions.object_id}"
  display_name   = "${var.project_name}-github-actions-${each.value}"
  description    = "Federated identity for GitHub Actions (${each.value} branch)"

  # GitHub repository in format: owner/repo
  audiences = ["api://AzureADTokenExchange"]
  issuer    = "https://token.actions.githubusercontent.com"

  # Use GitHub branch format: repo:owner/repo:ref:refs/heads/branch-name
  subject = "repo:${var.github_repository}:ref:refs/heads/${each.value}"

  # Ensure the application and service principal are created before the federated identity credential
  depends_on = [
    azuread_application.github_actions,
    azuread_service_principal.github_actions
  ]
}

# Legacy single federated identity credential (for backward compatibility)
# Only create if using old github_branch = "*" format without environments or branches
resource "azuread_application_federated_identity_credential" "github_actions" {
  count = length(var.github_environments) == 0 && length(var.github_branches) == 0 && var.github_branch == "*" ? 1 : 0

  # Reference the application's object_id (not client_id)
  application_id = "/applications/${azuread_application.github_actions.object_id}"
  display_name   = "${var.project_name}-github-actions-${var.environment}"
  description    = "Federated identity for GitHub Actions to authenticate to Azure (all branches)"

  # GitHub repository in format: owner/repo
  audiences = ["api://AzureADTokenExchange"]
  issuer    = "https://token.actions.githubusercontent.com"

  # Allow all branches
  subject = "repo:${var.github_repository}:*"

  # Ensure the application and service principal are created before the federated identity credential
  depends_on = [
    azuread_application.github_actions,
    azuread_service_principal.github_actions
  ]
}

# Grant GitHub Actions Service Principal access to Container Registry
resource "azurerm_role_assignment" "github_actions_acr_push" {
  scope                = var.container_registry_id
  role_definition_name = "AcrPush" # Allows push and pull
  principal_id         = azuread_service_principal.github_actions.id

  depends_on = [azuread_service_principal.github_actions]
}

# Grant GitHub Actions Service Principal access to Container Apps in shared resource group
resource "azurerm_role_assignment" "github_actions_container_apps_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor" # Allows updating Container Apps
  principal_id         = azuread_service_principal.github_actions.id

  depends_on = [azuread_service_principal.github_actions]
}

# Grant GitHub Actions Service Principal access to all environment resource groups
# This allows GitHub Actions to deploy to dev, staging, and prod environments
resource "azurerm_role_assignment" "github_actions_environment_contributor" {
  for_each = var.environment_resource_group_ids

  scope                = each.value
  role_definition_name = "Contributor" # Allows updating Container Apps in environment
  principal_id         = azuread_service_principal.github_actions.id

  depends_on = [azuread_service_principal.github_actions]
}

# Optional: Grant access to Key Vault (if needed for reading secrets during deployment)
resource "azurerm_role_assignment" "github_actions_key_vault_secrets_user" {
  count = var.key_vault_id != null ? 1 : 0

  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azuread_service_principal.github_actions.id

  depends_on = [azuread_service_principal.github_actions]
}
