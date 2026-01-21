# Terraform State Storage Configuration

## Overview

All Terraform state files are stored in a dedicated Azure Storage account: `lexiqaitfstate`

**Storage Account Details:**
- Resource Group: `lexiqai-tfstate-rg`
- Storage Account: `lexiqaitfstate`
- Container: `terraform-state`

## State File Structure

```
terraform-state/ (container)
├── shared/terraform.tfstate      ← Shared resources (ACR, GitHub OIDC, DNS, State Storage)
├── dev/terraform.tfstate         ← Dev environment resources
└── prod/terraform.tfstate        ← Prod environment resources (when created)
```

## Backend Configurations

### 1. Shared Resources (`infra/terraform/shared/`)

**File:** `backend-shared.tf`
```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "lexiqai-tfstate-rg"
    storage_account_name = "lexiqaitfstate"
    container_name       = "terraform-state"
    key                  = "shared/terraform.tfstate"
  }
}
```

**Status:** ✅ Configured
**State Key:** `shared/terraform.tfstate`

### 2. Environment Resources (`infra/terraform/`)

**File:** `backend.tf`
```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "lexiqai-tfstate-rg"
    storage_account_name = "lexiqaitfstate"
    container_name       = "terraform-state"
    key                  = "dev/terraform.tfstate"  # Default for local dev
  }
}
```

**Status:** ✅ Configured
**State Key:** `dev/terraform.tfstate` (default for local development)

**Note:** For production, CI/CD will dynamically generate this file with key: `prod/terraform.tfstate`

## Verification Checklist

Before migrating state, verify:

- [x] **Shared Resources Backend** (`backend-shared.tf`)
  - Storage account: `lexiqaitfstate` ✅
  - Key: `shared/terraform.tfstate` ✅
  - Container: `terraform-state` ✅

- [x] **Environment Resources Backend** (`backend.tf`)
  - Storage account: `lexiqaitfstate` ✅
  - Key: `dev/terraform.tfstate` ✅ (default)
  - Container: `terraform-state` ✅

- [ ] **Storage Account Created**
  - Resource group exists: `lexiqai-tfstate-rg`
  - Storage account exists: `lexiqaitfstate`
  - Container exists: `terraform-state`

- [ ] **GitHub OIDC Access**
  - Service principal has `Storage Blob Data Contributor` role
  - (This is automatically granted by the shared resources Terraform)

## Migration Order

1. **First: Create Storage Account** (using local state)
   ```bash
   cd infra/terraform/shared
   mv backend-shared.tf backend-shared.tf.disabled
   terraform init
   terraform apply -var-file=shared.tfvars
   ```

2. **Second: Migrate Shared Resources State**
   ```bash
   cd infra/terraform/shared
   mv backend-shared.tf.disabled backend-shared.tf
   terraform init -migrate-state  # Answer "yes"
   ```

3. **Third: Migrate Dev Environment State**
   ```bash
   cd infra/terraform
   cp terraform.tfstate terraform.tfstate.backup  # Backup
   terraform init -migrate-state  # Answer "yes"
   ```

4. **Fourth: Verify All States**
   ```bash
   # Check shared state
   cd infra/terraform/shared
   terraform state list
   
   # Check dev state
   cd ../..
   terraform state list
   
   # Verify in Azure Storage
   az storage blob list \
     --container-name terraform-state \
     --account-name lexiqaitfstate \
     --auth-mode login
   ```

## Production State

Production state will be created automatically when:
- You merge to `prod` branch, OR
- CI/CD workflow runs for production

The CI/CD pipeline will:
1. Generate `backend.tf` with key: `prod/terraform.tfstate`
2. Initialize Terraform (creates new state file)
3. Apply resources fresh (no migration needed)

## Troubleshooting

### Check if storage account exists:
```bash
az storage account show \
  --name lexiqaitfstate \
  --resource-group lexiqai-tfstate-rg \
  --query "{name:name, resourceGroup:resourceGroup}" \
  -o table
```

### List all state files:
```bash
az storage blob list \
  --container-name terraform-state \
  --account-name lexiqaitfstate \
  --auth-mode login \
  --query "[].name" \
  -o table
```

### Verify backend configuration:
```bash
# Shared resources
cd infra/terraform/shared
grep -A 5 "backend \"azurerm\"" backend-shared.tf

# Environment resources
cd ../..
grep -A 5 "backend \"azurerm\"" backend.tf
```
