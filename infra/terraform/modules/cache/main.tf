# Azure Cache for Redis
resource "azurerm_redis_cache" "main" {
  name                = "${var.project_name}-redis-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  capacity            = var.capacity
  family              = var.family
  sku_name            = var.sku_name  # Just "Basic", "Standard", or "Premium"
  non_ssl_port_enabled = var.enable_non_ssl_port  # Updated from deprecated enable_non_ssl_port
  minimum_tls_version = "1.2"
  redis_version       = var.redis_version

  # Note: Basic/Standard SKUs don't support VNet injection (subnet_id)
  # They use private endpoints instead (configured separately)
  # Premium SKU supports subnet_id for VNet injection
  # subnet_id = var.subnet_id  # Only for Premium SKU

  # Redis Configuration
  # Only include redis_configuration block if RDB backup is enabled
  dynamic "redis_configuration" {
    for_each = var.rdb_backup_enabled ? [1] : []
    content {
      rdb_backup_enabled          = var.rdb_backup_enabled
      rdb_backup_frequency        = var.rdb_backup_frequency
      rdb_backup_max_snapshot_count = var.rdb_backup_max_snapshot_count
      rdb_storage_connection_string = var.rdb_storage_connection_string
    }
  }

  # Patch Schedule (optional - can be configured later)
  # patch_schedule {
  #   day_of_week    = "Sunday"
  #   start_hour_utc = 2
  # }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-redis-${var.environment}"
    }
  )

  # No subnet_id dependency for Basic/Standard SKUs
}

