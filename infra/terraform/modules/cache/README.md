# Cache Module

Terraform module for creating Azure Cache for Redis.

## Status

✅ **Complete** - Implemented in Step 6 of Phase 1.

## Resources

- Azure Cache for Redis
- VNet integration (private access via delegated subnet)
- Network Security Group rules for secure access

## Important Notes

### VNet Integration
- **Basic/Standard SKUs**: Use **private endpoints** (not VNet injection)
  - No subnet delegation required
  - Private endpoint is created in the `private_endpoint_subnet`
  - Private DNS zone (`privatelink.redis.cache.windows.net`) for name resolution
- **Premium SKU**: Can use VNet injection (`subnet_id`) or private endpoints
  - We're using Basic/Standard, so private endpoints are the approach

### Configuration
- **Dev**: Basic C0, non-SSL port enabled for local compatibility
- **Prod**: Standard C1+, SSL only, RDB backups enabled

## Usage

```hcl
module "cache" {
  source = "./modules/cache"

  project_name = "lexiqai"
  environment  = "dev"
  location     = "westus"
  resource_group_name = "lexiqai-rg-dev"
  
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  vnet_id                   = module.network.vnet_id
  
  sku_name   = "Basic"
  family     = "C"
  capacity   = 0
  redis_version = "7.0"
  
  enable_non_ssl_port = true  # dev only
  rdb_backup_enabled = false  # dev only
  
  common_tags = {}
  
  depends_on = [module.network]
}
```

## Outputs

- `cache_id` - ID of the Redis cache
- `cache_name` - Name of the Redis cache
- `hostname` - Hostname (FQDN) of the Redis cache
- `port` - Non-SSL port (6379)
- `ssl_port` - SSL port (6380)
- `primary_access_key` - Primary access key (sensitive)
- `secondary_access_key` - Secondary access key (sensitive)
- `primary_connection_string` - Connection string template (sensitive)
- `private_endpoint_id` - ID of the Redis private endpoint
- `private_dns_zone_id` - ID of the Redis private DNS zone
