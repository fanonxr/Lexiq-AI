# Network Module

Terraform module for creating Azure Virtual Network, subnets, and Network Security Groups.

## Status

✅ **Complete** - Implemented in Step 4 of Phase 1.

## Planned Resources

- Virtual Network (VNet)
- Subnets:
  - Compute subnet (for Container Apps)
  - Data subnet (for databases)
  - Private endpoint subnet
- Network Security Groups (NSGs) with security rules
- Private DNS zones

## Usage

```hcl
module "network" {
  source = "./modules/network"

  project_name = var.project_name
  environment  = var.environment
  location     = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  vnet_address_space           = var.vnet_address_space
  compute_subnet_cidr          = var.compute_subnet_cidr
  data_subnet_cidr             = var.data_subnet_cidr
  private_endpoint_subnet_cidr = var.private_endpoint_subnet_cidr

  common_tags = var.common_tags
}
```

## Outputs

- `vnet_id` - ID of the Virtual Network
- `vnet_name` - Name of the Virtual Network
- `compute_subnet_id` - ID of the compute subnet
- `data_subnet_id` - ID of the data subnet
- `private_endpoint_subnet_id` - ID of the private endpoint subnet

