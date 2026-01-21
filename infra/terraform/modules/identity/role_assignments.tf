# Role Assignment: Contributor on Resource Group
# Allows the identity to manage resources within the resource group
resource "azurerm_role_assignment" "resource_group_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Role Assignment: PostgreSQL Flexible Server Contributor
# Allows the identity to access PostgreSQL Flexible Server
resource "azurerm_role_assignment" "postgres_contributor" {
  scope                = var.postgres_server_id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Role Assignment: Redis Cache Contributor
# Allows the identity to access Redis Cache
# Note: This is only needed for Azure Cache for Redis, not for containerized Redis
resource "azurerm_role_assignment" "redis_contributor" {
  count                = var.redis_cache_id != null ? 1 : 0
  scope                = var.redis_cache_id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Role Assignment: Storage Blob Data Contributor
# Allows the identity to read, write, and delete blobs in the storage account
# This is required for api-core and document-ingestion services to upload/download files
resource "azurerm_role_assignment" "storage_blob_contributor" {
  count                = var.storage_account_id != null ? 1 : 0
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_user_assigned_identity.main
  ]
}

# Role Assignment: Storage File Data SMB Share Contributor
# Allows the identity to read, write, and delete files in Azure File Shares
# Required for Qdrant and RabbitMQ persistent storage in Container Apps
# Note: Container Apps Environment Storage uses access keys, but this role ensures
# the identity can access file shares if needed for other operations
resource "azurerm_role_assignment" "storage_file_share_contributor" {
  count                = var.storage_account_id != null ? 1 : 0
  scope                = var.storage_account_id
  role_definition_name = "Storage File Data SMB Share Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id

  depends_on = [
    azurerm_user_assigned_identity.main
  ]
}

# Note: For PostgreSQL database access, the identity needs to be added as an Azure AD admin
# or granted specific database roles. This is typically done via SQL:
# CREATE USER "<identity-name>" FROM EXTERNAL PROVIDER;
# ALTER ROLE <role> GRANT TO "<identity-name>";
# This will be handled in application initialization or migration scripts.

