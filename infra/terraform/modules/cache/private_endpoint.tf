# Private Endpoint for Redis
# Basic/Standard SKUs require private endpoints for VNet integration
# Premium SKU can use subnet_id directly (VNet injection)
resource "azurerm_private_endpoint" "redis" {
  name                = "${var.project_name}-redis-pe-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.project_name}-redis-psc-${var.environment}"
    private_connection_resource_id = azurerm_redis_cache.main.id
    subresource_names              = ["redisCache"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "${var.project_name}-redis-dns-zone-group-${var.environment}"
    private_dns_zone_ids = [azurerm_private_dns_zone.redis.id]
  }

  tags = var.common_tags

  depends_on = [
    azurerm_redis_cache.main,
    azurerm_private_dns_zone.redis
  ]
}

# Private DNS Zone for Redis
resource "azurerm_private_dns_zone" "redis" {
  name                = "privatelink.redis.cache.windows.net"
  resource_group_name = var.resource_group_name

  tags = var.common_tags
}

# Link Private DNS Zone to VNet
resource "azurerm_private_dns_zone_virtual_network_link" "redis" {
  name                  = "${var.project_name}-redis-dns-link-${var.environment}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name  = azurerm_private_dns_zone.redis.name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false

  tags = var.common_tags

  depends_on = [var.vnet_id]
}

