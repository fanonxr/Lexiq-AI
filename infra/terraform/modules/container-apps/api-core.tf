# API Core Container App
# Main API service for authentication, user management, billing, and dashboard APIs
resource "azurerm_container_app" "api_core" {
  name                         = "${var.project_name}-api-core-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Define secrets (must be defined before they can be referenced in env blocks)
  # Secrets reference Key Vault secrets using key_vault_secret_id
  # Format: https://<vault-name>.vault.azure.net/secrets/<secret-name>
  # NOTE: Only include secrets that actually exist in Key Vault
  # Optional secrets (stripe-webhook-secret, google-client-secret, etc.) are only included
  # if they are provided via environment variables and created in secrets.tf
  dynamic "secret" {
    for_each = var.key_vault_name != null ? merge(
      {
        # Required secrets (always needed)
        "postgres-connection-string"    = "https://${var.key_vault_name}.vault.azure.net/secrets/postgres-connection-string"
        "internal-api-key"              = "https://${var.key_vault_name}.vault.azure.net/secrets/internal-api-key"
        "jwt-secret-key"                = "https://${var.key_vault_name}.vault.azure.net/secrets/jwt-secret-key"
        "appinsights-connection-string" = "https://${var.key_vault_name}.vault.azure.net/secrets/appinsights-connection-string"
        "azure-ad-b2c-client-secret"    = "https://${var.key_vault_name}.vault.azure.net/secrets/azure-ad-b2c-client-secret"
        "google-client-secret"          = "https://${var.key_vault_name}.vault.azure.net/secrets/google-client-secret"
        "stripe-secret-key"             = "https://${var.key_vault_name}.vault.azure.net/secrets/stripe-secret-key"
        "stripe-webhook-secret"         = "https://${var.key_vault_name}.vault.azure.net/secrets/stripe-webhook-secret"
        "twilio-auth-token"             = "https://${var.key_vault_name}.vault.azure.net/secrets/twilio-auth-token"
      },
      # Optional secrets - only include if you've provided the values and created them in Key Vault
      # Azure AD B2C Client Secret (created automatically by auth module if azure_ad_create_client_secret = true)
      # OR can be provided manually via TF_VAR_azure_ad_b2c_client_secret
      # "twilio-auth-token"            = "https://${var.key_vault_name}.vault.azure.net/secrets/twilio-auth-token",
    ) : {}
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
      name   = "api-core"
      image  = "${var.container_registry}/${var.project_name}/api-core:${var.image_tag}"
      cpu    = var.environment == "prod" ? 1.0 : 0.5
      memory = var.environment == "prod" ? "2Gi" : "1Gi"

      # Secrets from Key Vault
      env {
        name        = "DATABASE_URL"
        secret_name = "postgres-connection-string"
      }

      env {
        name        = "INTERNAL_API_KEY"
        secret_name = "internal-api-key"
      }

      env {
        name        = "JWT_SECRET_KEY"
        secret_name = "jwt-secret-key"
      }

      env {
        name        = "AZURE_AD_B2C_CLIENT_SECRET"
        secret_name = "azure-ad-b2c-client-secret"
      }

      env {
        name        = "GOOGLE_CLIENT_SECRET"
        secret_name = "google-client-secret"
      }

      env {
        name        = "STRIPE_SECRET_KEY"
        secret_name = "stripe-secret-key"
      }

      env {
        name        = "STRIPE_WEBHOOK_SECRET"
        secret_name = "stripe-webhook-secret"
      }

      env {
        name        = "TWILIO_AUTH_TOKEN"
        secret_name = "twilio-auth-token"
      }

      # Non-secret environment variables
      env {
        name  = "APP_ENV"
        value = var.environment
      }

      env {
        name  = "APP_NAME"
        value = "api-core"
      }

      env {
        name  = "DEBUG"
        value = var.environment == "prod" ? "false" : "true"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.environment == "prod" ? "INFO" : "DEBUG"
      }

      # Service URLs (constructed from other resources)
      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379" # Internal service name
      }

      env {
        name  = "COGNITIVE_ORCH_URL"
        value = "http://cognitive-orch:8001"
      }

      # RabbitMQ URL will be set after RabbitMQ container is created
      # For now, use a placeholder that will be updated
      env {
        name  = "RABBITMQ_URL"
        value = "amqp://rabbitmq:5672/" # Will reference RabbitMQ container app FQDN
      }

      # Application Insights
      env {
        name        = "AZURE_APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      # Health probe
      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8000
        interval_seconds = 30
        timeout          = 5
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8000
        interval_seconds = 10
        timeout          = 5
      }
    }
  }

  # External ingress for public API access
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-api-core-${var.environment}"
      Service = "api-core"
    }
  )
}
