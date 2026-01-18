# RabbitMQ Message Queue Container App
# Self-hosted message queue for document ingestion
resource "azurerm_container_app" "rabbitmq" {
  name                         = "${var.project_name}-rabbitmq-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Define secrets
  # Format: https://<vault-name>.vault.azure.net/secrets/<secret-name>
  dynamic "secret" {
    for_each = var.key_vault_name != null ? {
      "rabbitmq-password" = "https://${var.key_vault_name}.vault.azure.net/secrets/rabbitmq-password"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 1 : 0 # Scale to zero for dev
    max_replicas = var.environment == "prod" ? 2 : 1

    container {
      name = "rabbitmq"
      # Use ACR image if container_registry is provided, otherwise use public image
      image  = var.container_registry != "docker.io" ? "${var.container_registry}/${var.project_name}/rabbitmq:${var.environment}-latest" : "rabbitmq:3-management-alpine"
      cpu    = var.environment == "prod" ? 1.0 : 0.5
      memory = var.environment == "prod" ? "2Gi" : "1Gi"

      # RabbitMQ credentials from Key Vault
      env {
        name  = "RABBITMQ_DEFAULT_USER"
        value = "rabbitmq" # Can be made configurable if needed
      }

      env {
        name        = "RABBITMQ_DEFAULT_PASS"
        secret_name = "rabbitmq-password"
      }

      # RabbitMQ configuration
      env {
        name  = "RABBITMQ_DEFAULT_VHOST"
        value = "/"
      }

      # Enable management plugin for monitoring (port 15672)
      # Management UI is available internally but not exposed via ingress
      env {
        name  = "RABBITMQ_PLUGINS"
        value = "rabbitmq_management"
      }

      # Persistent storage for RabbitMQ data
      volume_mounts {
        name = "rabbitmq-storage"
        path = "/var/lib/rabbitmq"
      }

      # Health probe (TCP check on AMQP port)
      # Note: RabbitMQ management API requires authentication, so we use TCP health check
      # This checks if the AMQP port is accepting connections
      liveness_probe {
        transport        = "TCP"
        port             = 5672
        interval_seconds = 30
        timeout          = 10
      }

      readiness_probe {
        transport        = "TCP"
        port             = 5672
        interval_seconds = 10
        timeout          = 10
      }
    }

    # Volume for persistent storage
    volume {
      name         = "rabbitmq-storage"
      storage_type = "AzureFile"
      storage_name = var.rabbitmq_file_share_name
    }
  }

  # Internal ingress only - RabbitMQ should not be exposed externally
  # AMQP port for message queue
  ingress {
    external_enabled = false
    target_port      = 5672 # AMQP port
    transport        = "tcp"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-rabbitmq-${var.environment}"
      Service = "rabbitmq"
    }
  )
}
