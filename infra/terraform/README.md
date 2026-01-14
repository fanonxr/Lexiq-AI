# Terraform Infrastructure

This directory contains all Terraform configurations for provisioning and managing LexiqAI infrastructure on Microsoft Azure.

## Structure

```
terraform/
├── main.tf                    # Root module, provider, resource group
├── variables.tf                # Input variables
├── outputs.tf                  # Output values
├── backend.tf.example          # Example backend configuration
├── .terraformignore            # Files to ignore
├── terraform.tfvars.example    # Example variable values
├── dev.tfvars                 # Development environment variables
├── staging.tfvars             # Staging environment variables
├── prod.tfvars                # Production environment variables
└── modules/                   # Reusable Terraform modules
    ├── network/               # VNet, subnets, NSGs
    ├── database/              # PostgreSQL Flexible Server
    ├── identity/              # Managed Identities
    ├── container-apps/        # Container Apps Environment and services
    └── storage/               # Azure Blob Storage
```

## Prerequisites

1. **Azure CLI** installed and configured
   ```bash
   az login
   az account show
   ```

2. **Terraform** 1.5.0 or later installed
   ```bash
   terraform version
   ```

3. **Azure Subscription** with appropriate permissions
   - Contributor role on subscription or resource group
   - User Access Administrator (for role assignments)

**📖 For detailed setup instructions, see [Azure Setup Guide](/docs/foundation/azure-setup.md)**

## Quick Start

### 1. Initialize Terraform

```bash
cd infra/terraform
terraform init
```

### 2. Configure Variables

Set your Azure subscription and tenant IDs:

```bash
# Option 1: Environment variables
export TF_VAR_subscription_id=$(az account show --query id -o tsv)
export TF_VAR_tenant_id=$(az account show --query tenantId -o tsv)

# Option 2: Update dev.tfvars (but don't commit secrets)
```

### 3. Plan Changes

```bash
terraform plan -var-file=dev.tfvars
```

### 4. Apply Changes

```bash
terraform apply -var-file=dev.tfvars
```

### 5. Destroy Resources (when needed)

```bash
terraform destroy -var-file=dev.tfvars
```

## Backend Configuration

For production use, configure remote state storage:

1. Create Azure Storage Account for Terraform state
2. Copy `backend.tf.example` to `backend.tf`
3. Update with your storage account details
4. Re-run `terraform init` to migrate state

See [Terraform State Management](/docs/foundation/terraform-guide.md#state-management) for details.

## Environment Management

Each environment has its own variable file:

- **dev.tfvars** - Development (minimal resources, cost-optimized)
- **staging.tfvars** - Staging (moderate resources)
- **prod.tfvars** - Production (high availability, robust resources)

Always specify the environment when running Terraform:

```bash
terraform plan -var-file=dev.tfvars
terraform apply -var-file=staging.tfvars
```

## Modules

Modules are organized by resource type:

- **network** - Virtual Network, subnets, NSGs (Step 4)
- **database** - PostgreSQL Flexible Server (Step 5)
- **identity** - Managed Identities (Step 7)
- **container-apps** - Container Apps Environment and all containerized services (Step 8)
  - Includes Redis (migrated from Azure Cache for Redis), Qdrant, RabbitMQ, and all application services

Each module has its own README with usage examples.

## Security Best Practices

1. **Never commit secrets** - Use environment variables or Azure Key Vault
2. **Use remote state** - Store state in Azure Storage with versioning
3. **Enable state locking** - Prevent concurrent modifications
4. **Review plans** - Always review `terraform plan` before applying
5. **Tag resources** - All resources are tagged for cost tracking

## Common Commands

```bash
# Validate configuration
terraform validate

# Format code
terraform fmt -recursive

# Check formatting
terraform fmt -check -recursive

# Show current state
terraform show

# List resources
terraform state list

# Refresh state
terraform refresh -var-file=dev.tfvars
```

## Troubleshooting

### Authentication Issues

```bash
# Re-authenticate with Azure
az login

# Set subscription
az account set --subscription "<subscription-id>"
```

### State Lock Issues

If state is locked (e.g., from a failed operation):

```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

### Module Not Found

If modules aren't found after adding new ones:

```bash
terraform init -upgrade
```

## Documentation

- [Foundation Phase Plan](/docs/foundation/phase-1-plan.md)
- [Azure Setup Guide](/docs/foundation/azure-setup.md) - Azure authentication and prerequisites
- [Validation Checklist](./VALIDATION.md) - Step-by-step validation guide
- [Terraform Guide](/docs/foundation/terraform-guide.md) (coming soon)

## Status

- ✅ Step 2: Terraform Infrastructure Setup
- ✅ Step 3: Azure Resource Group & Core Configuration
- ✅ Step 4: Network Infrastructure
- ✅ Step 5: PostgreSQL Database Infrastructure
- ✅ Step 6: Redis Cache Infrastructure (Migrated to Container Apps)
- ✅ Step 7: Managed Identities & Authentication
- ✅ Step 8: Container Apps Infrastructure (Redis, Qdrant, RabbitMQ, and all application services)

