# Identity Module

Terraform module for creating Azure Managed Identities and role assignments.

## Status

✅ **Complete** - Implemented in Step 7 of Phase 1.

## Resources

- User-assigned Managed Identity
- Role assignments for:
  - Resource group access (Contributor)
  - PostgreSQL Flexible Server access (Contributor)
  - Redis Cache access (Contributor)

## Usage

```hcl
module "identity" {
  source = "./modules/identity"

  project_name = var.project_name
  environment  = var.environment
  location     = var.azure_location
  resource_group_id = azurerm_resource_group.main.id

  # Role assignments
  postgres_server_id = module.database.server_id
  redis_cache_id     = module.cache.cache_id

  common_tags = var.common_tags
}
```

## Important Notes

### PostgreSQL Database Access
The Contributor role on the PostgreSQL server allows the identity to manage the server, but for **database-level access**, the identity must be added as an Azure AD admin or granted specific database roles via SQL:

```sql
-- Add identity as Azure AD user
CREATE USER "<identity-name>" FROM EXTERNAL PROVIDER;

-- Grant specific roles
ALTER ROLE db_datareader GRANT TO "<identity-name>";
ALTER ROLE db_datawriter GRANT TO "<identity-name>";
```

This should be done in application initialization or migration scripts.

### Usage in Services
Services (like Container Apps) will use this identity by:
1. Assigning the identity to the service
2. Using Azure SDKs that automatically authenticate with the identity
3. No connection strings or secrets needed

## Outputs

- `client_id` - Client ID (Application ID) of the managed identity
- `principal_id` - Principal ID (Object ID) of the managed identity
- `resource_id` - Resource ID of the managed identity
- `name` - Name of the managed identity

