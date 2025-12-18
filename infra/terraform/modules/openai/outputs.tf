# Cognitive Account Outputs
output "account_name" {
  description = "Name of the Azure OpenAI Cognitive Services account"
  value       = azurerm_cognitive_account.openai.name
}

output "account_id" {
  description = "ID of the Azure OpenAI Cognitive Services account"
  value       = azurerm_cognitive_account.openai.id
}

output "endpoint" {
  description = "Endpoint URL for the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.endpoint
  sensitive   = true
}

output "primary_access_key" {
  description = "Primary access key for the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "secondary_access_key" {
  description = "Secondary access key for the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.secondary_access_key
  sensitive   = true
}

output "custom_subdomain_name" {
  description = "Custom subdomain name for the account"
  value       = azurerm_cognitive_account.openai.custom_subdomain_name
}

# Deployment Outputs
# Note: Deployments are commented out until quota is approved
# Uncomment these outputs when azurerm_cognitive_deployment.openai is uncommented in main.tf
output "deployment_ids" {
  description = "Map of deployment names to their resource IDs"
  value       = {}  # Empty until deployments are enabled
}

output "deployment_names" {
  description = "List of deployment names"
  value       = []  # Empty until deployments are enabled
}

# Key Vault Secret Outputs
output "key_vault_secret_name_api_key" {
  description = "Name of the Key Vault secret containing the API key (if Key Vault is configured)"
  value       = var.store_secrets_in_key_vault ? azurerm_key_vault_secret.openai_api_key[0].name : null
}

output "key_vault_secret_name_endpoint" {
  description = "Name of the Key Vault secret containing the endpoint URL (if Key Vault is configured)"
  value       = var.store_secrets_in_key_vault ? azurerm_key_vault_secret.openai_endpoint[0].name : null
}

output "key_vault_id" {
  description = "ID of the Key Vault where secrets are stored (if configured)"
  value       = var.key_vault_id
}

