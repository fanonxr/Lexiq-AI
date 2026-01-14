# Qdrant Vector Database Container App
# Self-hosted vector database for RAG and vector storage
resource "azurerm_container_app" "qdrant" {
  name                         = "${var.project_name}-qdrant-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity (for future use with Qdrant Cloud API key if needed)
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Define secrets (optional - only if Qdrant API key is needed)
  # Format: https://<vault-name>.vault.azure.net/secrets/<secret-name>
  # NOTE: qdrant-api-key is optional - only include if you've provided the value and created it in Key Vault
  dynamic "secret" {
    for_each = var.key_vault_name != null ? {} : {} # qdrant-api-key is optional - comment out if not needed
    # Uncomment the line below after you've added qdrant-api-key to Key Vault:
    # for_each = var.key_vault_name != null ? {
    #   "qdrant-api-key" = "https://${var.key_vault_name}.vault.azure.net/secrets/qdrant-api-key"
    # } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 1 : 0 # Scale to zero for dev
    max_replicas = var.environment == "prod" ? 3 : 1

    container {
      name = "qdrant"
      # Use ACR image if container_registry is provided, otherwise use public image
      image  = var.container_registry != "docker.io" ? "${var.container_registry}/${var.project_name}/qdrant:${var.environment}-latest" : "qdrant/qdrant:latest"
      cpu    = var.environment == "prod" ? 2.0 : 1.0
      memory = var.environment == "prod" ? "4Gi" : "2Gi"

      # Qdrant API key (optional - for Qdrant Cloud)
      # Uncomment after you've added qdrant-api-key to Key Vault:
      # dynamic "env" {
      #   for_each = var.key_vault_name != null ? [1] : []
      #   content {
      #     name        = "QDRANT_API_KEY"
      #     secret_name = "qdrant-api-key"
      #   }
      # }

      # Qdrant configuration
      env {
        name  = "QDRANT__SERVICE__GRPC_PORT"
        value = "6334"
      }

      env {
        name  = "QDRANT__SERVICE__HTTP_PORT"
        value = "6333"
      }

      # Persistent storage for Qdrant data
      volume_mounts {
        name = "qdrant-storage"
        path = "/qdrant/storage"
      }

      # Health probe
      liveness_probe {
        transport        = "HTTP"
        path             = "/healthz"
        port             = 6333
        interval_seconds = 30
        timeout          = 10
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/healthz"
        port             = 6333
        interval_seconds = 10
        timeout          = 10
      }
    }

    # Volume for persistent storage
    volume {
      name         = "qdrant-storage"
      storage_type = "AzureFile"
      storage_name = var.qdrant_file_share_name
    }
  }

  # Internal ingress only - Qdrant should not be exposed externally
  ingress {
    external_enabled = false
    target_port      = 6333 # REST API port
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-qdrant-${var.environment}"
      Service = "qdrant"
    }
  )
}
