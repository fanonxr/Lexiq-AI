output "server_id" {
  description = "ID of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.id
}

output "server_name" {
  description = "Name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.name
}

output "server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.fqdn
  sensitive   = true
}

output "database_name" {
  description = "Name of the PostgreSQL database"
  value       = azurerm_postgresql_flexible_server_database.main.name
}

output "database_id" {
  description = "ID of the PostgreSQL database"
  value       = azurerm_postgresql_flexible_server_database.main.id
}

# Private endpoint is not used when VNet integration is enabled
# When using delegated_subnet_id, the server is already private via VNet
# output "private_endpoint_id" {
#   description = "ID of the private endpoint"
#   value       = azurerm_private_endpoint.postgres.id
# }
# output "private_endpoint_fqdn" {
#   description = "Fully qualified domain name via private endpoint"
#   value       = azurerm_postgresql_flexible_server.main.fqdn
#   sensitive   = true
# }

output "connection_string_template" {
  description = "Connection string template (without password)"
  value       = "postgresql://${var.admin_username}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.database_name}"
  sensitive   = true
}

output "private_dns_zone_id" {
  description = "ID of the PostgreSQL private DNS zone"
  value       = azurerm_private_dns_zone.postgres.id
}

