# Voice Gateway Container App
# Handles Twilio WebSocket connections, STT, TTS, and Orchestrator integration
resource "azurerm_container_app" "voice_gateway" {
  name                         = "${var.project_name}-voice-gateway-${var.environment}"
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
      "deepgram-api-key" = "https://${var.key_vault_name}.vault.azure.net/secrets/deepgram-api-key"
      "cartesia-api-key" = "https://${var.key_vault_name}.vault.azure.net/secrets/cartesia-api-key"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 2 : 0 # Scale to zero for dev
    max_replicas = var.environment == "prod" ? 10 : 2

    container {
      name   = "voice-gateway"
      image  = "${var.container_registry}/${var.project_name}/voice-gateway:${var.image_tag}"
      cpu    = var.environment == "prod" ? 1.0 : 0.5
      memory = var.environment == "prod" ? "2Gi" : "1Gi"

      # Secrets from Key Vault
      env {
        name        = "DEEPGRAM_API_KEY"
        secret_name = "deepgram-api-key"
      }

      env {
        name        = "CARTESIA_API_KEY"
        secret_name = "cartesia-api-key"
      }

      # Non-secret environment variables
      env {
        name  = "PORT"
        value = "8080"
      }

      env {
        name  = "ORCHESTRATOR_URL"
        value = "cognitive-orch:50051" # Internal service name for gRPC
      }

      env {
        name  = "ORCHESTRATOR_TLS_ENABLED"
        value = "false"
      }

      env {
        name  = "ORCHESTRATOR_TIMEOUT"
        value = "30"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.environment == "prod" ? "info" : "debug"
      }

      env {
        name  = "LOG_PRETTY"
        value = "false"
      }

      env {
        name  = "METRICS_ENABLED"
        value = "true"
      }

      # Health probe
      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8080
        interval_seconds = 30
        timeout          = 10
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8080
        interval_seconds = 10
        timeout          = 10
      }
    }
  }

  # External ingress for Twilio WebSocket connections
  ingress {
    external_enabled = true
    target_port      = 8080
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-voice-gateway-${var.environment}"
      Service = "voice-gateway"
    }
  )
}
