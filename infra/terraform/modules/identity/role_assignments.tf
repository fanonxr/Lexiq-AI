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

# Note: For PostgreSQL database access, the identity needs to be added as an Azure AD admin
# or granted specific database roles. This is typically done via SQL:
# CREATE USER "<identity-name>" FROM EXTERNAL PROVIDER;
# ALTER ROLE <role> GRANT TO "<identity-name>";
# This will be handled in application initialization or migration scripts.

