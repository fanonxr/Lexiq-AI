output "application_id" {
  description = "Application (client) ID"
  value       = azuread_application.main.client_id
}

output "application_object_id" {
  description = "Application object ID"
  value       = azuread_application.main.object_id
}

output "service_principal_id" {
  description = "Service principal ID"
  value       = azuread_service_principal.main.id
}

output "service_principal_object_id" {
  description = "Service principal object ID"
  value       = azuread_service_principal.main.object_id
}

output "client_secret_id" {
  description = "Client secret ID (if created)"
  value       = var.create_client_secret ? azuread_application_password.main[0].id : null
  sensitive   = true
}

output "client_secret_value" {
  description = "Client secret value (if created). WARNING: This is sensitive data. Store in Key Vault."
  value       = var.create_client_secret ? azuread_application_password.main[0].value : null
  sensitive   = true
}

output "application_id_uri" {
  description = "Application ID URI (for exposed API)"
  value       = azuread_application.main.identifier_uris != null && length(azuread_application.main.identifier_uris) > 0 ? tolist(azuread_application.main.identifier_uris)[0] : "api://${azuread_application.main.client_id}"
}

output "authority_url" {
  description = "Authority URL for authentication (tenant-specific)"
  value       = "https://login.microsoftonline.com/${data.azuread_client_config.current.tenant_id}"
}

output "tenant_id" {
  description = "Azure AD tenant ID"
  value       = data.azuread_client_config.current.tenant_id
}

# Data source for current Azure AD client config
data "azuread_client_config" "current" {}
