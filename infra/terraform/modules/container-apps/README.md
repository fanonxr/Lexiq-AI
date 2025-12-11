# Container Apps Module

Terraform module for creating Azure Container Apps Environment and Container Apps.

## Status

🚧 **In Development** - This module will be implemented in Phase 2.

## Planned Resources

- Azure Container Apps Environment
- Container Apps for each service:
  - Voice Gateway
  - Cognitive Orchestrator
  - API Core
  - Integration Worker

## Usage

```hcl
module "container_apps" {
  source = "./modules/container-apps"

  project_name = var.project_name
  environment  = var.environment
  location     = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  subnet_id = module.network.compute_subnet_id
  managed_identity_id = module.identity.resource_id

  common_tags = var.common_tags
}
```

## Outputs

- `container_app_environment_id` - ID of the Container Apps Environment
- `container_app_environment_name` - Name of the Container Apps Environment

