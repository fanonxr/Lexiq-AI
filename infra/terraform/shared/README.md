# Shared Resources Terraform Configuration

This directory contains Terraform configuration for resources that are shared across all environments (dev, staging, prod).

## Shared Resources

1. **Azure Container Registry (ACR)** - Single registry for all container images
2. **GitHub OIDC Application** - Single Azure AD app for GitHub Actions authentication
3. **Azure DNS Zone** - Single DNS zone for all environments (if using Azure DNS)

## Files

- `main.tf` - Main Terraform configuration for shared resources
- `variables.tf` - Variable definitions
- `outputs.tf` - Output values (used by environment-specific configs)
- `shared.tfvars` - Variable values for shared resources
- `README.md` - This file

## Usage

### Using Makefile Commands (Recommended)

All commands should be run from the **project root** using Makefile targets:

```bash
# From project root (not from infra/terraform/shared/)
make terraform-shared-init    # Initialize Terraform
make terraform-shared-plan    # Review changes
make terraform-shared-apply   # Apply changes
make terraform-shared-output  # View outputs
make terraform-shared-validate # Validate configuration
```

### Manual Commands

If you prefer to run commands manually, you **must** run them from the `infra/terraform/shared/` directory:

```bash
cd infra/terraform/shared

# Source environment variables (subscription_id, tenant_id)
source ../../.env  # Or set TF_VAR_subscription_id and TF_VAR_tenant_id

# Initialize Terraform
terraform init

# Plan Changes
terraform plan -var-file=shared.tfvars

# Apply Changes
terraform apply -var-file=shared.tfvars

# View Outputs
terraform output
```

**⚠️ Important:** Do NOT run terraform commands from `infra/terraform/` directory for shared resources. Always use `infra/terraform/shared/` or the Makefile targets from the project root.

## Important Notes

1. **Container Registry Name**: The ACR name must be globally unique. The current name is `lexiqaiacrshared`. If this is taken, update it in `main.tf`.

2. **GitHub OIDC**: The GitHub OIDC module will need to be updated to support multiple branches/environments. See Phase 2 of the implementation plan.

3. **DNS Zone**: Only created if `dns_zone_name` is provided in `shared.tfvars`. Leave empty if using external DNS.

4. **Backend Configuration**: Update the `backend "azurerm"` block in `main.tf` with your Terraform state storage configuration, or configure via CLI.

## Environment Variables

Some values may need to be set via environment variables:

```bash
export TF_VAR_subscription_id="<your-subscription-id>"
export TF_VAR_tenant_id="<your-tenant-id>"
```

Or source from your `.env` file:

```bash
source ../../.env
```

## Next Steps

After creating shared resources:

1. Update environment-specific Terraform configs to reference shared resources (Phase 3)
2. Migrate existing resources (Phase 4)
3. Update GitHub Actions workflows (Phase 5)

See `docs/deploy/SHARED_RESOURCES_IMPLEMENTATION.md` for complete migration guide.
