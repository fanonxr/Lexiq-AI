# Cognitive Orchestrator Container App
# LLM routing, RAG, conversation state management, and tool execution
resource "azurerm_container_app" "cognitive_orch" {
  name                         = "${var.project_name}-cognitive-orch-${var.environment}"
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
  # NOTE: Only include secrets that actually exist in Key Vault
  # Optional secrets (anthropic-api-key, groq-api-key) are only included
  # if they are provided via environment variables and created in secrets.tf
  dynamic "secret" {
    for_each = var.key_vault_name != null ? merge(
      {
        # Required secrets (always needed)
        "internal-api-key"              = "https://${var.key_vault_name}.vault.azure.net/secrets/internal-api-key"
        "redis-password"                = "https://${var.key_vault_name}.vault.azure.net/secrets/${var.redis_password_secret_name}"
        "appinsights-connection-string" = "https://${var.key_vault_name}.vault.azure.net/secrets/appinsights-connection-string"
        "anthropic-api-key"             = "https://${var.key_vault_name}.vault.azure.net/secrets/anthropic-api-key"
      },
      # Optional secrets - only include if you've provided the values and created them in Key Vault
    ) : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 2 : 0
    max_replicas = var.environment == "prod" ? 10 : 2

    container {
      name   = "cognitive-orch"
      image  = "${var.container_registry}/${var.project_name}/cognitive-orch:${var.image_tag}"
      cpu    = var.environment == "prod" ? 2.0 : 1.0
      memory = var.environment == "prod" ? "4Gi" : "2Gi"

      # Secrets from Key Vault
      # Note: Azure OpenAI was removed - if you need it, manually create the secret in Key Vault
      # env {
      #   name        = "AZURE_API_KEY"
      #   secret_name = "azure-openai-api-key"
      # }

      env {
        name        = "ANTHROPIC_API_KEY"
        secret_name = "anthropic-api-key"
      }

      # GROQ_API_KEY removed - not currently used
      # env {
      #   name        = "GROQ_API_KEY"
      #   secret_name = "groq-api-key"
      # }

      env {
        name        = "CORE_API_API_KEY"
        secret_name = "internal-api-key"
      }

      env {
        name        = "REDIS_PASSWORD"
        secret_name = var.redis_password_secret_name
      }

      # Application Insights
      env {
        name        = "AZURE_APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      # Non-secret environment variables
      env {
        name  = "APP_NAME"
        value = "cognitive-orch"
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
        value = "8001"
      }

      env {
        name  = "GRPC_PORT"
        value = "50051"
      }

      # Service URLs - use internal service names
      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379"
      }

      env {
        name  = "QDRANT_URL"
        value = "http://qdrant:6333"
      }

      env {
        name  = "CORE_API_URL"
        value = "http://api-core:8000"
      }

      env {
        name  = "INTEGRATION_WORKER_URL"
        value = "http://integration-worker-webhooks:8002"
      }

      # Health probes
      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8001
        interval_seconds = 30
        timeout          = 10
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/ready"
        port             = 8001
        interval_seconds = 10
        timeout          = 10
      }
    }
  }

  # Internal ingress for HTTP, external for gRPC (if needed)
  # For now, use internal only - gRPC can be accessed via internal network
  ingress {
    external_enabled = false # Internal only - accessed by voice-gateway
    target_port      = 8001
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-cognitive-orch-${var.environment}"
      Service = "cognitive-orch"
    }
  )
}
