# Infrastructure as Code

This directory contains all Infrastructure as Code (IaC) configurations for LexiqAI.

## Structure

- **`terraform/`** - Terraform configurations
  - Main Terraform modules and resources
  - Environment-specific variable files
  - Backend configuration

## Terraform

All Azure infrastructure is managed through Terraform. Manual changes in the Azure Portal are prohibited for staging and production environments.

### Quick Start

```bash
# Initialize Terraform
cd infra/terraform
terraform init

# Plan changes
terraform plan -var-file=dev.tfvars

# Apply changes
terraform apply -var-file=dev.tfvars
```

See [Terraform Guide](/docs/foundation/terraform-guide.md) for detailed documentation.

## Resources Managed

- Virtual Network (VNet) and subnets
- Network Security Groups (NSGs)
- Azure Database for PostgreSQL (Flexible Server)
- Azure Cache for Redis
- Azure Container Apps Environment
- Managed Identities
- Private DNS zones
- Storage Accounts

## Environments

- **dev** - Development environment
- **staging** - Staging environment
- **prod** - Production environment

Each environment has its own variable file (`dev.tfvars`, `staging.tfvars`, `prod.tfvars`).

