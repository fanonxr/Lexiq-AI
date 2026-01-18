# Secrets Management
# This file creates Key Vault secrets from Terraform variables
# Secrets are marked as sensitive to prevent exposure in state/plan files
#
# IMPORTANT: Secrets are passed via environment variables (TF_VAR_*)
# and stored in Key Vault. They will still appear in Terraform state files,
# so state files must be protected (use remote state with encryption).

# Google OAuth Client Secret
resource "azurerm_key_vault_secret" "google_client_secret" {
  count = var.google_client_secret != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "google-client-secret"
  value        = var.google_client_secret
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "oauth-secret"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "oauth"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Twilio Account Token (Auth Token)
resource "azurerm_key_vault_secret" "twilio_auth_token" {
  count = var.twilio_account_token != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "twilio-auth-token"
  value        = var.twilio_account_token
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-token"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-token"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Twilio API Key (optional)
resource "azurerm_key_vault_secret" "twilio_api_key" {
  count = var.twilio_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "twilio-api-key"
  value        = var.twilio_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Stripe Publishable Key (not a secret, but stored for consistency)
resource "azurerm_key_vault_secret" "stripe_publishable_key" {
  count = var.stripe_publishable_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "stripe-publishable-key"
  value        = var.stripe_publishable_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Stripe Webhook Secret
resource "azurerm_key_vault_secret" "stripe_webhook_secret" {
  count = var.stripe_webhook_secret != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "stripe-webhook-secret"
  value        = var.stripe_webhook_secret
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "webhook-secret"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "webhook-secret"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Stripe Secret Key
resource "azurerm_key_vault_secret" "stripe_secret_key" {
  count = var.stripe_secret_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "stripe-secret-key"
  value        = var.stripe_secret_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Deepgram API Key
resource "azurerm_key_vault_secret" "deepgram_api_key" {
  count = var.deepgram_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "deepgram-api-key"
  value        = var.deepgram_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Cartesia API Key
resource "azurerm_key_vault_secret" "cartesia_api_key" {
  count = var.cartesia_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "cartesia-api-key"
  value        = var.cartesia_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# PostgreSQL Connection String
# Constructed from database module outputs
resource "azurerm_key_vault_secret" "postgres_connection_string" {
  count = length(azurerm_key_vault.main) > 0 && var.postgres_admin_password != "" ? 1 : 0

  name         = "postgres-connection-string"
  value        = "postgresql://${var.postgres_admin_username}:${var.postgres_admin_password}@${module.database.server_fqdn}:5432/${module.database.database_name}"
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "connection-string"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "database"
    }
  )

  depends_on = [
    azurerm_key_vault.main,
    module.database
  ]
}

# Internal API Key (for service-to-service authentication)
# This should be a strong random string - generate it or provide via variable
resource "azurerm_key_vault_secret" "internal_api_key" {
  count = var.internal_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "internal-api-key"
  value        = var.internal_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# JWT Secret Key (for token signing)
# This should be a strong random string - generate it or provide via variable
resource "azurerm_key_vault_secret" "jwt_secret_key" {
  count = var.jwt_secret_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "jwt-secret-key"
  value        = var.jwt_secret_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "jwt-secret"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "jwt"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Azure AD Client Secret (from auth module)
# Note: The auth module stores the client secret as "azure-ad-b2c-client-secret" in Key Vault
# This resource creates an alias "azure-ad-client-secret" for backward compatibility
# If you need a separate value, provide it via variable
resource "azurerm_key_vault_secret" "azure_ad_client_secret" {
  count = length(azurerm_key_vault.main) > 0 && var.azure_ad_client_secret != "" ? 1 : 0

  name         = "azure-ad-client-secret"
  value        = var.azure_ad_client_secret
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "oauth-secret"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "oauth"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Azure AD B2C Client Secret (if different from above)
# Note: If using Azure AD B2C, this should be set separately
# For now, we'll use the same as azure-ad-client-secret
resource "azurerm_key_vault_secret" "azure_ad_b2c_client_secret" {
  count = var.azure_ad_b2c_client_secret != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "azure-ad-b2c-client-secret"
  value        = var.azure_ad_b2c_client_secret
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "oauth-secret"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "oauth"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Anthropic API Key
resource "azurerm_key_vault_secret" "anthropic_api_key" {
  count = var.anthropic_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "anthropic-api-key"
  value        = var.anthropic_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Groq API Key
resource "azurerm_key_vault_secret" "groq_api_key" {
  count = var.groq_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "groq-api-key"
  value        = var.groq_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Qdrant API Key (optional - for Qdrant Cloud)
resource "azurerm_key_vault_secret" "qdrant_api_key" {
  count = var.qdrant_api_key != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "qdrant-api-key"
  value        = var.qdrant_api_key
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "api-key"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "api-key"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# RabbitMQ Password
# Generate a random password or provide via variable
resource "azurerm_key_vault_secret" "rabbitmq_password" {
  count = var.rabbitmq_password != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "rabbitmq-password"
  value        = var.rabbitmq_password
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "password"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "password"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Redis Password
# Generate a random password or provide via variable
resource "azurerm_key_vault_secret" "redis_password" {
  count = var.redis_password != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0

  name         = "redis-password"
  value        = var.redis_password
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "password"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
      SecretType  = "password"
    }
  )

  depends_on = [azurerm_key_vault.main]
}

# Webhook Secret (for integration worker webhooks)
# NOTE: This is currently NOT USED in the application code
# Microsoft Graph webhooks use validation tokens in headers, not shared secrets
# Google Calendar webhooks (Phase 5) are not yet implemented
# Keeping this commented out until it's actually needed
# resource "azurerm_key_vault_secret" "webhook_secret" {
#   count = var.webhook_secret != "" && length(azurerm_key_vault.main) > 0 ? 1 : 0
#
#   name         = "webhook-secret"
#   value        = var.webhook_secret
#   key_vault_id = azurerm_key_vault.main[0].id
#
#   content_type = "webhook-secret"
#
#   tags = merge(
#     var.common_tags,
#     {
#       Environment = var.environment
#       ManagedBy   = "Terraform"
#       SecretType  = "webhook-secret"
#     }
#   )
#
#   depends_on = [azurerm_key_vault.main]
# }
