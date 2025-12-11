# Private Endpoint for PostgreSQL
# Note: When using VNet integration with delegated subnet (delegated_subnet_id),
# private endpoints are NOT supported. The server is already private via VNet integration.
# Private endpoints are only supported when using public network access or
# when the server is created without VNet delegation.
#
# Since we're using delegated_subnet_id for VNet integration, we skip the private endpoint.
# The server is accessible via the VNet and private DNS zone.
#
# If you need private endpoints (for scenarios without VNet integration),
# you would need to create the server without delegated_subnet_id and use
# public_network_access_enabled = false with private endpoints instead.

# resource "azurerm_private_endpoint" "postgres" {
#   name                = "${var.project_name}-db-pe-${var.environment}"
#   location            = var.location
#   resource_group_name = var.resource_group_name
#   subnet_id           = var.private_endpoint_subnet_id
#
#   private_service_connection {
#     name                           = "${var.project_name}-db-psc-${var.environment}"
#     private_connection_resource_id  = azurerm_postgresql_flexible_server.main.id
#     subresource_names              = ["postgresqlServer"]
#     is_manual_connection           = false
#   }
#
#   private_dns_zone_group {
#     name                 = "${var.project_name}-db-dns-zone-group-${var.environment}"
#     private_dns_zone_ids = [azurerm_private_dns_zone.postgres.id]
#   }
#
#   tags = var.common_tags
#
#   depends_on = [
#     azurerm_postgresql_flexible_server.main,
#     azurerm_private_dns_zone.postgres
#   ]
# }

