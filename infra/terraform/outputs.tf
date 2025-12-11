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

# Redis Outputs
output "redis_cache_name" {
  description = "Name of the Redis cache"
  value       = module.cache.cache_name
}

output "redis_hostname" {
  description = "Hostname of the Redis cache"
  value       = module.cache.hostname
  sensitive   = true
}

output "redis_port" {
  description = "Port of the Redis cache (non-SSL)"
  value       = module.cache.port
}

output "redis_ssl_port" {
  description = "SSL port of the Redis cache"
  value       = module.cache.ssl_port
}

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

