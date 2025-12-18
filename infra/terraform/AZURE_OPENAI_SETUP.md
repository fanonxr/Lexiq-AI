# Azure OpenAI Infrastructure Setup

This document explains how to set up Azure OpenAI resources using Terraform.

## Overview

The Azure OpenAI module (`modules/openai/`) creates:
- Azure OpenAI Cognitive Services account
- Model deployments (e.g., gpt-4o, gpt-4-turbo)
- Key Vault secrets for API keys and endpoints (optional)

## Prerequisites

1. **Azure OpenAI Access**: Your Azure subscription must have access to Azure OpenAI. If you don't have access:
   - Request access at: https://aka.ms/oai/access
   - Approval can take 1-3 business days

2. **Terraform**: Ensure Terraform is installed and configured

3. **Azure CLI**: Logged in with appropriate permissions

## Quick Start

1. **Update your `.tfvars` file** (e.g., `dev.tfvars`):

```hcl
# Azure OpenAI Configuration
openai_sku_name = "S0"
openai_public_network_access_enabled = true
openai_key_vault_enabled = true

openai_model_deployments = {
  "gpt-4o" = {
    model_name    = "gpt-4o"
    model_version = "2024-08-06"  # Specific version required (2024-08-06 is the default)
    scale_type    = "Standard"
    scale_capacity = 10
    scale_tier    = "Standard"
    scale_size    = null
  }
}
```

2. **Initialize and apply Terraform**:

```bash
cd infra/terraform
terraform init
terraform plan -var-file=dev.tfvars
terraform apply -var-file=dev.tfvars
```

3. **Get the configuration values**:

```bash
# Get endpoint
terraform output openai_endpoint

# Get API key (if Key Vault enabled)
az keyvault secret show \
  --vault-name $(terraform output -raw key_vault_name) \
  --name openai-api-key \
  --query value -o tsv
```

## Environment Variables

After deployment, configure your application:

### Option 1: Direct from Terraform outputs

```bash
export AZURE_API_KEY=$(terraform output -raw openai_primary_access_key)
export AZURE_API_BASE=$(terraform output -raw openai_endpoint)
export AZURE_API_VERSION=2024-02-15-preview
```

### Option 2: From Key Vault (Recommended for Production)

```bash
VAULT_NAME=$(terraform output -raw key_vault_name)
export AZURE_API_KEY=$(az keyvault secret show --vault-name $VAULT_NAME --name openai-api-key --query value -o tsv)
export AZURE_API_BASE=$(az keyvault secret show --vault-name $VAULT_NAME --name openai-endpoint --query value -o tsv)
export AZURE_API_VERSION=2024-02-15-preview
```

### Option 3: Use Managed Identity (Best for Container Apps)

If your Container Apps use Managed Identity, you can access Key Vault secrets without storing keys:

```python
# In your application code
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://<vault-name>.vault.azure.net/", credential=credential)

api_key = client.get_secret("openai-api-key").value
endpoint = client.get_secret("openai-endpoint").value
```

## Model Deployments

The module deploys models specified in `openai_model_deployments`. Each deployment:
- Creates a model endpoint (e.g., `gpt-4o`)
- Configures scaling (capacity, tier, size)
- Takes 5-15 minutes to complete

### Supported Models

Available models in your account (check with `az cognitiveservices account list-models`):
- `gpt-4o` - Versions: `2024-05-13`, `2024-08-06` (default), `2024-11-20`
- `gpt-4o-mini` - Version: `2024-07-18`
- `gpt-4.1` - Version: `2025-04-14`
- `gpt-4.1-mini` - Version: `2025-04-14`
- `gpt-4.1-nano` - Version: `2025-04-14`
- `o1` - Version: `2024-12-17`
- `o1-mini` - Version: `2024-09-12`

**Important**: Azure OpenAI requires specific version numbers, not `"latest"`. Use the exact version string.

### Model Deployment Names

The deployment name (key in the map) is what you'll use in your application:

```python
# In LiteLLM format
model_name = "azure/gpt-4o"  # Uses deployment named "gpt-4o"
```

## Key Vault Integration

When `openai_key_vault_enabled = true`:
- API key is stored as `openai-api-key`
- Endpoint URL is stored as `openai-endpoint`
- Secrets are automatically created and updated

### Access Policies

The Key Vault is created with an access policy for the current user. For production:
- Add Managed Identity access policies
- Restrict network access
- Enable purge protection

## Troubleshooting

### "Resource not found" or "Access denied"
- Ensure Azure OpenAI access is approved for your subscription
- Check that you're using the correct subscription

### Model deployment fails
- Some models may not be available in all regions
- Check model availability: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models
- Deployment can take 10-15 minutes

### Key Vault access issues
- Ensure you have "Key Vault Secrets User" role
- Check access policies in Azure Portal

## Cost Considerations

- **S0 SKU**: Pay-as-you-go, suitable for development
- **S1+ SKU**: Higher throughput, better for production
- **Model deployments**: Each deployment has its own cost
- Monitor usage in Azure Cost Management

## Next Steps

1. Deploy the infrastructure
2. Configure your Cognitive Orchestrator service with the environment variables
3. Test the LLM service using the test endpoints
4. Monitor usage and costs

## References

- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Terraform Azure Provider - Cognitive Account](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/cognitive_account)
- [LiteLLM Azure OpenAI Guide](https://docs.litellm.ai/docs/providers/azure_openai)

