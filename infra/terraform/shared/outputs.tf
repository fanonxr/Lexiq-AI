# Container Registry Outputs
output "container_registry_name" {
  description = "Name of the shared container registry"
  value       = azurerm_container_registry.shared.name
}

output "container_registry_login_server" {
  description = "Login server URL for the shared container registry"
  value       = azurerm_container_registry.shared.login_server
}

output "container_registry_id" {
  description = "Resource ID of the shared container registry"
  value       = azurerm_container_registry.shared.id
}

# GitHub OIDC Outputs
output "github_oidc_application_id" {
  description = "Application (client) ID for GitHub Actions OIDC"
  value       = module.github_oidc.application_id
}

output "github_oidc_service_principal_id" {
  description = "Service Principal ID for GitHub Actions"
  value       = module.github_oidc.service_principal_id
}

output "github_oidc_tenant_id" {
  description = "Azure AD Tenant ID for GitHub Actions"
  value       = module.github_oidc.tenant_id
}

# DNS Zone Outputs
output "dns_zone_name" {
  description = "Name of the shared DNS zone"
  value       = var.dns_zone_name != "" ? azurerm_dns_zone.shared[0].name : null
}

output "dns_zone_name_servers" {
  description = "Name servers for the shared DNS zone"
  value       = var.dns_zone_name != "" ? azurerm_dns_zone.shared[0].name_servers : null
}

# Resource Group Output
output "resource_group_name" {
  description = "Name of the shared resource group"
  value       = azurerm_resource_group.shared.name
}

output "resource_group_id" {
  description = "Resource ID of the shared resource group"
  value       = azurerm_resource_group.shared.id
}

# Terraform State Storage Outputs
output "tfstate_resource_group_name" {
  description = "Name of the Terraform state storage resource group"
  value       = azurerm_resource_group.tfstate.name
}

output "tfstate_storage_account_name" {
  description = "Name of the Terraform state storage account"
  value       = azurerm_storage_account.tfstate.name
}

output "tfstate_storage_account_id" {
  description = "Resource ID of the Terraform state storage account"
  value       = azurerm_storage_account.tfstate.id
}

output "tfstate_container_name" {
  description = "Name of the Terraform state container"
  value       = azurerm_storage_container.tfstate.name
}
