output "client_id" {
  description = "Client ID (Application ID) of the user-assigned managed identity"
  value       = azurerm_user_assigned_identity.main.client_id
}

output "principal_id" {
  description = "Principal ID (Object ID) of the user-assigned managed identity"
  value       = azurerm_user_assigned_identity.main.principal_id
}

output "resource_id" {
  description = "Resource ID of the user-assigned managed identity"
  value       = azurerm_user_assigned_identity.main.id
}

output "name" {
  description = "Name of the user-assigned managed identity"
  value       = azurerm_user_assigned_identity.main.name
}

