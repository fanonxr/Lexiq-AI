# Document Ingestion Container App
# Processes knowledge base files for RAG: parsing, chunking, embedding, vector storage
# NOTE: Depends on init jobs completing (database role grants) before starting
resource "azurerm_container_app" "document_ingestion" {
  name                         = "${var.project_name}-document-ingestion-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity (for Azure Storage access)
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Ensure init jobs are created before this app
  depends_on = [
    azurerm_container_app_job.grant_database_roles
  ]

  # Define secrets
  # Format: https://<vault-name>.vault.azure.net/secrets/<secret-name>
  dynamic "secret" {
    for_each = var.key_vault_name != null ? {
      "internal-api-key"              = "https://${var.key_vault_name}.vault.azure.net/secrets/internal-api-key"
      "appinsights-connection-string" = "https://${var.key_vault_name}.vault.azure.net/secrets/appinsights-connection-string"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 1 : 0 # Scale to zero for dev
    max_replicas = var.environment == "prod" ? 5 : 2

    container {
      name   = "document-ingestion"
      image  = "${var.container_registry}/${var.project_name}/document-ingestion:${var.image_tag}"
      cpu    = var.environment == "prod" ? 2.0 : 1.0
      memory = var.environment == "prod" ? "4Gi" : "2Gi"

      # Secrets from Key Vault
      env {
        name        = "CORE_API_API_KEY"
        secret_name = "internal-api-key"
      }

      # Application Insights
      env {
        name        = "AZURE_APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      # Non-secret environment variables
      env {
        name  = "APP_NAME"
        value = "document-ingestion"
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "DEBUG"
        value = var.environment == "prod" ? "false" : "true"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.environment == "prod" ? "INFO" : "DEBUG"
      }

      env {
        name  = "HOST"
        value = "0.0.0.0"
      }

      env {
        name  = "PORT"
        value = "8003"
      }

      # Service URLs - use internal service names
      env {
        name  = "RABBITMQ_URL"
        value = "amqp://rabbitmq:5672/"
      }

      env {
        name  = "QDRANT_URL"
        value = "http://qdrant:6333"
      }

      env {
        name  = "CORE_API_URL"
        value = "http://api-core:8000"
      }

      # Storage - use Managed Identity
      env {
        name  = "STORAGE_ACCOUNT_NAME"
        value = var.storage_account_name
      }

      env {
        name  = "STORAGE_USE_MANAGED_IDENTITY"
        value = "true"
      }

      # Health probe
      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8003
        interval_seconds = 30
        timeout          = 10
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/ready"
        port             = 8003
        interval_seconds = 10
        timeout          = 10
      }
    }
  }

  # Internal ingress only - Document ingestion is a worker service
  ingress {
    external_enabled = false
    target_port      = 8003
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-document-ingestion-${var.environment}"
      Service = "document-ingestion"
    }
  )
}
