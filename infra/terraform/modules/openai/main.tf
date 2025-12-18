# Azure OpenAI Account (Cognitive Services)
# This creates an Azure OpenAI resource that provides access to GPT models

resource "azurerm_cognitive_account" "openai" {
  name                = "${var.project_name}-openai-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = var.sku_name

  # Public network access (can be restricted with private endpoints later)
  public_network_access_enabled = var.public_network_access_enabled

  # Custom subdomain name (optional, but recommended for cleaner URLs)
  custom_subdomain_name = var.custom_subdomain_name != null ? var.custom_subdomain_name : "${var.project_name}-openai-${var.environment}"

  # Tags
  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-openai-${var.environment}"
    }
  )
}

# Azure OpenAI Deployment (Model)
# Deploys a specific model (e.g., gpt-4o, gpt-4-turbo) to the account
# resource "azurerm_cognitive_deployment" "openai" {
  # for_each = var.model_deployments

  # name                 = each.key
  # cognitive_account_id = azurerm_cognitive_account.openai.id
  # model {
    # format  = "OpenAI"
    # name    = each.value.model_name
    # version = each.value.model_version
  # }

  # rai_policy_name = var.rai_policy_name
  
  # Scale configuration - only type and capacity are required
  # Note: tier and size fields may not be supported or may cause errors
  # scale {
    # type     = each.value.scale_type
    # capacity = each.value.scale_capacity
  # }

  # Note: azurerm_cognitive_deployment doesn't support tags
  # Tags are applied at the account level (azurerm_cognitive_account)
# }

# Key Vault Secret for API Key
# Store the primary key in Key Vault for secure access
resource "azurerm_key_vault_secret" "openai_api_key" {
  count = var.store_secrets_in_key_vault ? 1 : 0

  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = var.key_vault_id

  content_type = "Azure OpenAI API Key"
  tags = merge(
    var.common_tags,
    {
      Resource = "Azure OpenAI"
    }
  )

  depends_on = [azurerm_cognitive_account.openai]
}

# Key Vault Secret for Endpoint URL
resource "azurerm_key_vault_secret" "openai_endpoint" {
  count = var.store_secrets_in_key_vault ? 1 : 0

  name         = "openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = var.key_vault_id

  content_type = "Azure OpenAI Endpoint URL"
  tags = merge(
    var.common_tags,
    {
      Resource = "Azure OpenAI"
    }
  )

  depends_on = [azurerm_cognitive_account.openai]
}

