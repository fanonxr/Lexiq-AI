# Database Module

Terraform module for creating Azure Database for PostgreSQL Flexible Server.

## Status

✅ **Complete** - Implemented in Step 5 of Phase 1.

## Resources

- Azure Database for PostgreSQL Flexible Server
- PostgreSQL database
- VNet integration (private access via delegated subnet)
- Private DNS zone for service discovery

## Note on Vector Storage

Vector storage and RAG capabilities will be handled by **Qdrant** (separate vector database service).
PostgreSQL is used for relational data only (users, calls, billing, firm data, etc.).

## Usage

```hcl
module "database" {
  source = "./modules/database"

  project_name = var.project_name
  environment  = var.environment
  location     = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  subnet_id = module.network.data_subnet_id

  admin_username      = var.postgres_admin_username
  sku_name            = var.postgres_sku_name
  storage_mb           = var.postgres_storage_mb
  backup_retention_days = var.postgres_backup_retention_days
  postgres_version     = var.postgres_version

  common_tags = var.common_tags
}
```

## Outputs

- `server_name` - Name of the PostgreSQL server
- `server_fqdn` - Fully qualified domain name
- `database_name` - Name of the database
- `private_endpoint_id` - ID of the private endpoint

