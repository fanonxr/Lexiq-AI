# Resource Group Outputs
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

# Network Outputs
output "vnet_id" {
  description = "ID of the Virtual Network"
  value       = module.network.vnet_id
}

output "vnet_name" {
  description = "Name of the Virtual Network"
  value       = module.network.vnet_name
}

output "compute_subnet_id" {
  description = "ID of the compute subnet"
  value       = module.network.compute_subnet_id
}

output "data_subnet_id" {
  description = "ID of the data subnet"
  value       = module.network.data_subnet_id
}

output "private_endpoint_subnet_id" {
  description = "ID of the private endpoint subnet"
  value       = module.network.private_endpoint_subnet_id
}

output "private_dns_zone_name" {
  description = "Name of the private DNS zone"
  value       = module.network.private_dns_zone_name
}

# Database Outputs
output "postgres_server_name" {
  description = "Name of the PostgreSQL server"
  value       = module.database.server_name
}

output "postgres_server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL server"
  value       = module.database.server_fqdn
  sensitive   = true
}

output "postgres_database_name" {
  description = "Name of the PostgreSQL database"
  value       = module.database.database_name
}

# Private endpoint is not used when VNet integration is enabled
# output "postgres_private_endpoint_id" {
#   description = "ID of the PostgreSQL private endpoint"
#   value       = module.database.private_endpoint_id
# }

# Redis Outputs (Container App)
# Note: Redis has been migrated from Azure Cache for Redis to Container App
output "redis_container_app_name" {
  description = "Name of the Redis container app"
  value       = try(module.container_apps.redis_container_app_name, null)
}

output "redis_hostname" {
  description = "Hostname (FQDN) of the Redis container app for internal connections"
  value       = try(module.container_apps.redis_hostname, null)
  sensitive   = false # Internal FQDN is not sensitive
}

output "redis_port" {
  description = "Port number for Redis connections"
  value       = try(module.container_apps.redis_port, 6379)
}

output "redis_url" {
  description = "Redis connection URL (without password - password should come from Key Vault)"
  value       = try(module.container_apps.redis_url, null)
  sensitive   = false # URL without password is not sensitive
}

# Legacy outputs (commented out - kept for reference during migration)
# output "redis_cache_name" {
#   description = "Name of the Redis cache (deprecated - use redis_container_app_name)"
#   value       = module.cache.cache_name
# }
#
# output "redis_ssl_port" {
#   description = "SSL port of the Redis cache (deprecated - Redis container uses standard port 6379)"
#   value       = module.cache.ssl_port
# }

# Identity Outputs
output "managed_identity_client_id" {
  description = "Client ID (Application ID) of the user-assigned managed identity"
  value       = module.identity.client_id
}

output "managed_identity_principal_id" {
  description = "Principal ID (Object ID) of the user-assigned managed identity"
  value       = module.identity.principal_id
}

output "managed_identity_resource_id" {
  description = "Resource ID of the user-assigned managed identity"
  value       = module.identity.resource_id
}

output "managed_identity_name" {
  description = "Name of the user-assigned managed identity"
  value       = module.identity.name
}

# Key Vault Outputs
output "key_vault_name" {
  description = "Name of the Key Vault (if enabled)"
  value       = length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].name : null
}

output "key_vault_id" {
  description = "ID of the Key Vault (if enabled)"
  value       = length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].id : null
}

# Azure Container Registry Outputs - Now using shared ACR
output "container_registry_name" {
  description = "Name of the shared Azure Container Registry"
  value       = data.azurerm_container_registry.shared.name
}

output "container_registry_login_server" {
  description = "Login server URL for the shared Azure Container Registry"
  value       = data.azurerm_container_registry.shared.login_server
}

output "container_registry_id" {
  description = "ID of the shared Azure Container Registry"
  value       = data.azurerm_container_registry.shared.id
}

# Storage Account Outputs
output "storage_account_name" {
  description = "Name of the storage account"
  value       = module.storage.storage_account_name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = module.storage.storage_account_id
}

output "storage_primary_blob_endpoint" {
  description = "Primary blob endpoint URL"
  value       = module.storage.primary_blob_endpoint
}

# Log Analytics Workspace Outputs
output "log_analytics_workspace_id" {
  description = "ID of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.main.name
}

# Application Insights Outputs
output "application_insights_id" {
  description = "ID of the Application Insights resource"
  value       = azurerm_application_insights.main.id
}

output "application_insights_name" {
  description = "Name of the Application Insights resource"
  value       = azurerm_application_insights.main.name
}

output "application_insights_connection_string" {
  description = "Connection string for Application Insights (sensitive)"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  description = "Instrumentation key for Application Insights (sensitive)"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

# Container Apps Public Endpoints
output "api_core_url" {
  description = "Public URL for API Core (custom domain if configured, otherwise default FQDN)"
  value       = module.container_apps.api_core_url
}

output "api_core_hostname" {
  description = "Hostname for API Core (default Container Apps FQDN)"
  value       = module.container_apps.api_core_hostname
}

output "voice_gateway_url" {
  description = "Public URL for Voice Gateway (custom domain if configured, otherwise default FQDN)"
  value       = module.container_apps.voice_gateway_url
}

output "voice_gateway_hostname" {
  description = "Hostname for Voice Gateway (default Container Apps FQDN)"
  value       = module.container_apps.voice_gateway_hostname
}

# DNS Zone Outputs - Now using shared DNS zone (if configured)
output "dns_zone_name" {
  description = "Name of the shared Azure DNS zone (if configured)"
  value       = var.dns_zone_name != "" ? var.dns_zone_name : null
}

output "dns_zone_name_servers" {
  description = "Name servers for the shared Azure DNS zone (if configured)"
  value       = var.dns_zone_name != "" && length(data.azurerm_dns_zone.shared) > 0 ? data.azurerm_dns_zone.shared[0].name_servers : null
}

# Static Web App Outputs
output "static_web_app_name" {
  description = "Name of the Static Web App"
  value       = azurerm_static_web_app.frontend.name
}

output "static_web_app_default_host_name" {
  description = "Default hostname for the Static Web App (e.g., 'lexiqai-web-dev.azurestaticapps.net')"
  value       = azurerm_static_web_app.frontend.default_host_name
}

output "static_web_app_url" {
  description = "URL of the Static Web App (custom domain if configured, otherwise default hostname)"
  value       = var.static_web_app_custom_domain != "" ? "https://${var.static_web_app_custom_domain}" : "https://${azurerm_static_web_app.frontend.default_host_name}"
}

output "static_web_app_custom_domain" {
  description = "Custom domain for Static Web App (if configured)"
  value       = var.static_web_app_custom_domain != "" ? var.static_web_app_custom_domain : null
}

output "static_web_app_api_key" {
  description = "API key for Static Web App (for deployment via GitHub Actions or Azure DevOps)"
  value       = azurerm_static_web_app.frontend.api_key
  sensitive   = true
}

# Azure AD App Registration Outputs
output "azure_ad_application_id" {
  description = "Azure AD Application (Client) ID"
  value       = module.auth.application_id
}

output "azure_ad_application_object_id" {
  description = "Azure AD Application Object ID"
  value       = module.auth.application_object_id
}

output "azure_ad_service_principal_id" {
  description = "Azure AD Service Principal ID"
  value       = module.auth.service_principal_id
}

output "azure_ad_authority_url" {
  description = "Azure AD Authority URL for authentication"
  value       = module.auth.authority_url
}

# GitHub OIDC Outputs - MIGRATED TO SHARED RESOURCES
# These outputs are now available from the shared resources (see infra/terraform/shared/outputs.tf)
# Keeping these outputs for backward compatibility but they will return null
# To get the actual values, use: terraform output -module=shared github_oidc_application_id
output "github_oidc_application_id" {
  description = "Application (client) ID for GitHub Actions OIDC authentication (deprecated - use shared resources output)"
  value       = null # Now available from shared resources
}

output "github_oidc_service_principal_id" {
  description = "Service Principal ID for GitHub Actions (deprecated - use shared resources output)"
  value       = null # Now available from shared resources
  sensitive   = true
}

output "github_oidc_tenant_id" {
  description = "Azure AD Tenant ID for GitHub Actions (deprecated - use shared resources output)"
  value       = null # Now available from shared resources
}

output "azure_ad_tenant_id" {
  description = "Azure AD Tenant ID"
  value       = module.auth.tenant_id
}

output "azure_ad_application_id_uri" {
  description = "Azure AD Application ID URI (for exposed API)"
  value       = module.auth.application_id_uri
}

# Subscription Output (for CI/CD)
output "subscription_id" {
  description = "Azure subscription ID (for GitHub Actions)"
  value       = var.subscription_id
  sensitive   = true
}
