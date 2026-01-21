# Azure Storage Account for Blob Storage
# Used for storing knowledge base documents for RAG

resource "azurerm_storage_account" "main" {
  name                     = "${var.project_name}storage${var.environment}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = var.account_tier
  account_replication_type = var.account_replication_type
  account_kind             = "StorageV2" # General Purpose V2

  # Enable HTTPS only
  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"

  # Network access
  public_network_access_enabled = var.public_network_access_enabled

  # Network rules (optional - for IP allowlists, VNet restrictions, etc.)
  # If public_network_access_enabled = false, these rules control access
  # If public_network_access_enabled = true, these rules can still restrict access
  dynamic "network_rules" {
    for_each = var.network_rules != null ? [1] : []
    content {
      default_action             = var.network_rules.default_action
      bypass                     = var.network_rules.bypass
      ip_rules                   = var.network_rules.ip_rules
      virtual_network_subnet_ids = var.network_rules.virtual_network_subnet_ids
    }
  }

  # Allow blob public access (disabled for security)
  allow_nested_items_to_be_public = false

  # Blob properties
  blob_properties {
    # Enable versioning for document recovery
    versioning_enabled = var.versioning_enabled

    # Soft delete for blob recovery
    delete_retention_policy {
      days = var.blob_soft_delete_retention_days
    }

    # Change feed (optional, for audit trail)
    change_feed_enabled = var.change_feed_enabled

    # Container delete retention
    container_delete_retention_policy {
      days = var.container_soft_delete_retention_days
    }
  }

  # Lifecycle management (optional)
  # Can be configured to move old blobs to cool/archive tiers

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-storage-${var.environment}"
      Purpose = "RAG Document Storage"
    }
  )
}

# Note: Blob Containers are NOT created in Terraform
# Containers are created dynamically in code when firms are created:
# - Container name: `firm-{firm_id}-documents`
# - Created via Azure SDK/API when firm is created
# - Access controlled via Managed Identity with container-level RBAC

# Azure File Shares for Container Apps persistent storage
# These are used for persistent volumes in Container Apps (Qdrant, RabbitMQ, etc.)

resource "azurerm_storage_share" "qdrant" {
  name                 = "qdrant-storage"
  storage_account_name = azurerm_storage_account.main.name
  quota                = var.environment == "prod" ? 100 : 10 # GB

  # Access tier (Hot for frequently accessed data)
  access_tier = "Hot"
}

resource "azurerm_storage_share" "rabbitmq" {
  name                 = "rabbitmq-storage"
  storage_account_name = azurerm_storage_account.main.name
  quota                = var.environment == "prod" ? 50 : 5 # GB

  # Access tier (Hot for frequently accessed data)
  access_tier = "Hot"
}
