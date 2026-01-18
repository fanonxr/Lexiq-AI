# Storage Account Outputs
output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "primary_blob_endpoint" {
  description = "Primary blob endpoint URL"
  value       = azurerm_storage_account.main.primary_blob_endpoint
  sensitive   = false
}

output "primary_blob_host" {
  description = "Primary blob host (for connection strings)"
  value       = azurerm_storage_account.main.primary_blob_host
  sensitive   = false
}

output "primary_access_key" {
  description = "Primary access key (use Managed Identity instead when possible)"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "secondary_access_key" {
  description = "Secondary access key (use Managed Identity instead when possible)"
  value       = azurerm_storage_account.main.secondary_access_key
  sensitive   = true
}

output "primary_connection_string" {
  description = "Primary connection string (use Managed Identity instead when possible)"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

# File Share Outputs (for Container Apps persistent storage)
output "qdrant_file_share_name" {
  description = "Name of the Azure File Share for Qdrant persistent storage"
  value       = azurerm_storage_share.qdrant.name
}

output "rabbitmq_file_share_name" {
  description = "Name of the Azure File Share for RabbitMQ persistent storage"
  value       = azurerm_storage_share.rabbitmq.name
}

# Note: Blob Containers are created dynamically in code, not via Terraform
# Container naming convention: `firm-{firm_id}-documents`

