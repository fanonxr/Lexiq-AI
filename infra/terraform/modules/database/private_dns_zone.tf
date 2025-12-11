# Private DNS Zone for PostgreSQL Flexible Server
# Azure requires a specific DNS zone format for PostgreSQL: postgres.database.azure.com
resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = var.resource_group_name

  tags = var.common_tags
}

# Link Private DNS Zone to VNet
resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${var.project_name}-postgres-dns-link-${var.environment}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false

  tags = var.common_tags

  # Explicit dependency on VNet to ensure it exists
  depends_on = [var.vnet_id]
}


