# Integration Worker Container App (Celery Worker)
# Handles background job processing for calendar synchronization
# NOTE: Depends on init jobs completing (database role grants) before starting
resource "azurerm_container_app" "integration_worker" {
  name                         = "${var.project_name}-integration-worker-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity
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
  # NOTE: Only include secrets that actually exist in Key Vault
  # Optional secrets (azure-ad-client-secret, google-client-secret) are only included
  # if they are provided via environment variables and created in secrets.tf
  dynamic "secret" {
    for_each = var.key_vault_name != null ? merge(
      {
        # Required secrets (always needed)
        "postgres-connection-string" = "https://${var.key_vault_name}.vault.azure.net/secrets/postgres-connection-string"
        "internal-api-key"           = "https://${var.key_vault_name}.vault.azure.net/secrets/internal-api-key"
      },
      # Optional secrets - only include if you've provided the values and created them in Key Vault
      # Uncomment these lines after you've added the secrets to Key Vault:
      # "azure-ad-client-secret"      = "https://${var.key_vault_name}.vault.azure.net/secrets/azure-ad-client-secret",
      # "google-client-secret"        = "https://${var.key_vault_name}.vault.azure.net/secrets/google-client-secret",
    ) : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 2 : 0 # Scale to zero for dev
    max_replicas = var.environment == "prod" ? 5 : 2

    container {
      name   = "integration-worker"
      image  = "${var.container_registry}/${var.project_name}/integration-worker:${var.image_tag}"
      cpu    = var.environment == "prod" ? 1.0 : 0.5
      memory = var.environment == "prod" ? "2Gi" : "1Gi"

      # Secrets from Key Vault
      env {
        name        = "DATABASE_URL"
        secret_name = "postgres-connection-string"
      }

      env {
        name        = "CORE_API_API_KEY"
        secret_name = "internal-api-key"
      }

      # Optional secrets - uncomment after adding them to Key Vault:
      # env {
      #   name        = "AZURE_AD_CLIENT_SECRET"
      #   secret_name = "azure-ad-client-secret"
      # }

      # env {
      #   name        = "GOOGLE_CLIENT_SECRET"
      #   secret_name = "google-client-secret"
      # }

      # Non-secret environment variables
      env {
        name  = "SERVICE_NAME"
        value = "integration-worker"
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379"
      }

      env {
        name  = "API_CORE_URL"
        value = "http://api-core:8000"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.environment == "prod" ? "INFO" : "DEBUG"
      }

      # Celery command
      args = [
        "celery",
        "-A", "integration_worker.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=4"
      ]
    }
  }

  # No ingress - Celery worker doesn't expose HTTP endpoints
  # Health checks can be done via Celery inspect commands

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-integration-worker-${var.environment}"
      Service = "integration-worker"
    }
  )
}

# Integration Worker Beat Container App (Celery Scheduler)
# Triggers scheduled tasks: calendar sync every 15 min, token refresh every hour
# Note: Container App names must be <= 32 characters
# NOTE: Depends on init jobs completing (database role grants) before starting
resource "azurerm_container_app" "integration_worker_beat" {
  name                         = "${var.project_name}-iw-beat-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity
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
      "postgres-connection-string" = "https://${var.key_vault_name}.vault.azure.net/secrets/postgres-connection-string"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    min_replicas = var.environment == "prod" ? 1 : 0 # Scale to zero for dev
    max_replicas = 1                                 # Only one beat scheduler should run

    container {
      name   = "integration-worker-beat"
      image  = "${var.container_registry}/${var.project_name}/integration-worker:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      # Secrets from Key Vault
      env {
        name        = "DATABASE_URL"
        secret_name = "postgres-connection-string"
      }

      # Non-secret environment variables
      env {
        name  = "SERVICE_NAME"
        value = "integration-worker-beat"
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379"
      }

      env {
        name  = "API_CORE_URL"
        value = "http://api-core:8000"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.environment == "prod" ? "INFO" : "DEBUG"
      }

      # Celery beat command
      args = [
        "celery",
        "-A", "integration_worker.celery_app",
        "beat",
        "--loglevel=info"
      ]
    }
  }

  # No ingress - Celery beat doesn't expose HTTP endpoints

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-integration-worker-beat-${var.environment}"
      Service = "integration-worker-beat"
    }
  )
}

# Integration Worker Webhooks Container App
# Receives real-time notifications from Microsoft Graph, Google Calendar, etc.
# Note: Container App names must be <= 32 characters
# NOTE: Depends on init jobs completing (database role grants) before starting
resource "azurerm_container_app" "integration_worker_webhooks" {
  name                         = "${var.project_name}-iw-webhooks-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  # Assign Managed Identity
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
  # NOTE: Only include secrets that actually exist in Key Vault
  # Optional secrets (azure-ad-client-secret) are only included
  # if they are provided via environment variables and created in secrets.tf
  dynamic "secret" {
    for_each = var.key_vault_name != null ? merge(
      {
        # Required secrets (always needed)
        "postgres-connection-string"    = "https://${var.key_vault_name}.vault.azure.net/secrets/postgres-connection-string"
        "appinsights-connection-string" = "https://${var.key_vault_name}.vault.azure.net/secrets/appinsights-connection-string"
      },
      # Optional secrets - only include if you've provided the values and created them in Key Vault
      # Uncomment these lines after you've added the secrets to Key Vault:
      # "azure-ad-client-secret"      = "https://${var.key_vault_name}.vault.azure.net/secrets/azure-ad-client-secret",
      # Note: webhook-secret is not currently used - Microsoft Graph uses validation tokens, not secrets
    ) : {}
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
      name   = "integration-worker-webhooks"
      image  = "${var.container_registry}/${var.project_name}/integration-worker:${var.image_tag}"
      cpu    = var.environment == "prod" ? 1.0 : 0.5
      memory = var.environment == "prod" ? "2Gi" : "1Gi"

      # Secrets from Key Vault
      env {
        name        = "DATABASE_URL"
        secret_name = "postgres-connection-string"
      }

      # Optional secrets - uncomment after adding them to Key Vault:
      # env {
      #   name        = "AZURE_AD_CLIENT_SECRET"
      #   secret_name = "azure-ad-client-secret"
      # }

      # Note: WEBHOOK_SECRET is not currently used - Microsoft Graph webhooks use validation tokens
      # If you need webhook signature validation in the future, uncomment this:
      # env {
      #   name        = "WEBHOOK_SECRET"
      #   secret_name = "webhook-secret"
      # }

      # Application Insights
      env {
        name        = "AZURE_APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      # Non-secret environment variables
      env {
        name  = "SERVICE_NAME"
        value = "integration-worker-webhooks"
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "REDIS_URL"
        value = "redis://redis:6379"
      }

      env {
        name  = "API_CORE_URL"
        value = "http://api-core:8000"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.environment == "prod" ? "INFO" : "DEBUG"
      }

      # FastAPI command
      args = [
        "uvicorn",
        "integration_worker.main:app",
        "--host", "0.0.0.0",
        "--port", "8002"
      ]

      # Health probe
      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8002
        interval_seconds = 30
        timeout          = 10
      }

      readiness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8002
        interval_seconds = 10
        timeout          = 10
      }
    }
  }

  # External ingress for webhook endpoints
  ingress {
    external_enabled = true
    target_port      = 8002
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = merge(
    var.common_tags,
    {
      Name    = "${var.project_name}-integration-worker-webhooks-${var.environment}"
      Service = "integration-worker-webhooks"
    }
  )
}
