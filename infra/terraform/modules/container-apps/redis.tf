# Redis Container App
# Self-hosted Redis for cost savings vs Azure Cache for Redis
resource "azurerm_container_app" "redis" {
  name                         = "${var.project_name}-redis-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity (for Key Vault access if needed)
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Define secrets
  # Format: https://<vault-name>.vault.azure.net/secrets/<secret-name>
  dynamic "secret" {
    for_each = var.key_vault_name != null ? {
      "redis-password" = "https://${var.key_vault_name}.vault.azure.net/secrets/${var.redis_password_secret_name}"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.redis_min_replicas
    max_replicas = var.redis_max_replicas

    container {
      name = "redis"
      # Use ACR image if container_registry is provided, otherwise use public image
      image  = var.container_registry != "docker.io" ? "${var.container_registry}/${var.project_name}/redis:${var.environment}-latest" : var.redis_image
      cpu    = var.redis_cpu
      memory = var.redis_memory

      # Redis password from Key Vault
      # Note: Container Apps will inject the secret value as the environment variable
      # If Key Vault is not configured, the secret must be set manually in Container Apps
      env {
        name        = "REDIS_PASSWORD"
        secret_name = var.redis_password_secret_name
      }

      # Redis configuration arguments
      # AOF (Append Only File) persistence enabled for durability
      # Use a shell command to read the password from environment variable
      # The redis:7-alpine image includes sh, so we can use it to construct the command
      # Note: $$ escapes to $ in Terraform, which becomes $REDIS_PASSWORD in the container
      args = [
        "sh",
        "-c",
        "exec redis-server --appendonly yes --requirepass \"$$REDIS_PASSWORD\""
      ]

      # Volume mount for Redis persistence (AOF files)
      # Note: Container Apps supports Azure File shares for persistent storage
      # For now, we'll use in-memory with AOF (data will be lost on restart but can be rebuilt)
      # TODO: Add persistent volume mount when needed
    }
  }

  # Internal ingress only - Redis should not be exposed externally
  ingress {
    external_enabled = false
    target_port      = 6379
    transport        = "tcp"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-redis-${var.environment}"
      Service = "redis"
    }
  )
}
