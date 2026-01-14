output "application_id" {
  description = "Application (client) ID for GitHub Actions"
  value       = azuread_application.github_actions.client_id
}

output "service_principal_id" {
  description = "Service Principal ID"
  value       = azuread_service_principal.github_actions.id
}

output "tenant_id" {
  description = "Azure AD Tenant ID"
  value       = azuread_application.github_actions.publisher_domain != null ? data.azurerm_client_config.current.tenant_id : null
}

# Data source for tenant ID
data "azurerm_client_config" "current" {}
