# Azure OpenAI Module

This module creates and manages an Azure OpenAI resource (Cognitive Services account) with model deployments.

## Features

- Creates Azure OpenAI Cognitive Services account
- Deploys specified models (e.g., gpt-4o, gpt-4-turbo)
- Stores API key and endpoint in Key Vault (optional)
- Configurable SKU and scaling options
- Supports custom subdomain names

## Usage

```hcl
module "openai" {
  source = "./modules/openai"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  sku_name = "S0"  # Standard tier

  # Deploy models
  model_deployments = {
    "gpt-4o" = {
      model_name    = "gpt-4o"
      model_version = "latest"
      scale_type    = "Standard"
      scale_capacity = 10
      scale_tier    = "Standard"
      scale_size    = "1"
    }
    "gpt-4-turbo" = {
      model_name    = "gpt-4-turbo"
      model_version = "latest"
      scale_type    = "Standard"
      scale_capacity = 10
      scale_tier    = "Standard"
      scale_size    = "1"
    }
  }

  # Store secrets in Key Vault (optional)
  key_vault_id = azurerm_key_vault.main.id

  common_tags = var.common_tags
}
```

## Outputs

- `endpoint`: Endpoint URL for API calls
- `primary_access_key`: Primary API key (sensitive)
- `deployment_names`: List of deployed model names
- `key_vault_secret_name_api_key`: Key Vault secret name for API key (if Key Vault configured)

## Environment Variables

After deployment, configure your application with:

```bash
AZURE_API_KEY=<primary_access_key>
AZURE_API_BASE=<endpoint>
AZURE_API_VERSION=2024-02-15-preview
```

Or retrieve from Key Vault:

```bash
AZURE_API_KEY=$(az keyvault secret show --vault-name <vault-name> --name openai-api-key --query value -o tsv)
AZURE_API_BASE=$(az keyvault secret show --vault-name <vault-name> --name openai-endpoint --query value -o tsv)
```

## Notes

- Azure OpenAI requires approval/access in your subscription
- Model deployments may take several minutes to complete
- SKU S0 is suitable for development, consider S1+ for production
- Custom subdomain names must be globally unique

