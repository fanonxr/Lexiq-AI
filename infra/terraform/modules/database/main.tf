# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${var.project_name}-db-${var.environment}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = var.postgres_version
  delegated_subnet_id           = var.data_subnet_id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false # Required when using VNet integration
  administrator_login           = var.admin_username
  administrator_password        = var.admin_password

  # SKU Configuration
  # Note: Workload type is determined by SKU:
  # - B_Standard_* (Burstable) = DevTest workload
  # - GP_Standard_* (General Purpose) = GeneralPurpose workload
  sku_name   = var.sku_name
  storage_mb = var.storage_mb

  # Backup Configuration
  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = var.geo_redundant_backup_enabled

  # High Availability (for production)
  dynamic "high_availability" {
    for_each = var.high_availability_enabled ? [1] : []
    content {
      mode                      = "ZoneRedundant"
      standby_availability_zone = 2
    }
  }

  # Maintenance Window
  maintenance_window {
    day_of_week  = 0 # Sunday
    start_hour   = 2
    start_minute = 0
  }

  # Authentication
  authentication {
    active_directory_auth_enabled = false # Will be enabled later with Managed Identity
    password_auth_enabled         = true
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-db-${var.environment}"
    }
  )

  depends_on = [
    azurerm_private_dns_zone.postgres,
    var.data_subnet_id, # Ensure subnet exists before creating server
  ]
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Note: Vector storage will be handled by Qdrant (separate vector database)
# PostgreSQL is used for relational data only (users, calls, billing, etc.)
# Qdrant will be deployed separately for RAG and vector search capabilities

