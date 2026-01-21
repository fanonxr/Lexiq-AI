# Bootstrap Terraform State Storage

## The Chicken-and-Egg Problem

The Terraform state storage account is created BY the shared resources Terraform configuration, but Terraform needs that storage account FOR its backend. This creates a circular dependency.

## Solution: Two-Phase Approach

We'll use local state for the FIRST apply to create the storage account, then migrate to remote state.

## Step-by-Step Bootstrap Process

### Phase 1: Create Storage Account with Local State

1. **Navigate to shared resources directory**:
   ```bash
   cd infra/terraform/shared
   ```

2. **Initialize Terraform WITHOUT the backend** (uses local state):
   ```bash
   terraform init -backend=false
   ```
   
   This tells Terraform to ignore the backend configuration and use local state for now.

3. **Review what will be created**:
   ```bash
   terraform plan -var-file=shared.tfvars
   ```
   
   You should see the storage account and related resources being created.

4. **Apply to create the storage account**:
   ```bash
   terraform apply -var-file=shared.tfvars
   ```
   
   This creates:
   - Resource group: `lexiqai-tfstate-rg`
   - Storage account: `lexiqaitfstate`
   - Container: `terraform-state`
   - Role assignment for GitHub OIDC

5. **Verify the storage account was created**:
   ```bash
   az storage account show \
     --name lexiqaitfstate \
     --resource-group lexiqai-tfstate-rg \
     --query "{name:name, resourceGroup:resourceGroup, location:location}" \
     -o table
   ```

### Phase 2: Migrate to Remote State

Now that the storage account exists, we can migrate the state to use it.

1. **Backup your local state** (safety first!):
   ```bash
   cp terraform.tfstate terraform.tfstate.local-backup-$(date +%Y%m%d-%H%M%S)
   ```

2. **Re-initialize with the remote backend**:
   ```bash
   terraform init -migrate-state
   ```
   
   Terraform will detect that:
   - You have a backend configuration
   - You have existing local state
   - The backend storage account now exists
   
   It will prompt: **"Do you want to copy existing state to the new backend?"**
   
   Answer: **`yes`**

3. **Verify the migration**:
   ```bash
   # Check that state is now remote
   terraform state list
   
   # Verify state file exists in Azure Storage
   az storage blob list \
     --container-name terraform-state \
     --account-name lexiqaitfstate \
     --auth-mode login \
     --query "[?name=='shared/terraform.tfstate']" \
     -o table
   ```

4. **Test that everything works**:
   ```bash
   # Run a plan to ensure Terraform can read remote state
   terraform plan -var-file=shared.tfvars
   ```
   
   This should show no changes (since we just applied).

## Alternative: Manual Storage Account Creation

If you prefer to create the storage account manually first (avoiding the bootstrap), you can:

1. **Create storage account manually**:
   ```bash
   az group create --name lexiqai-tfstate-rg --location eastus
   az storage account create \
     --name lexiqaitfstate \
     --resource-group lexiqai-tfstate-rg \
     --location eastus \
     --sku Standard_LRS
   az storage container create \
     --name terraform-state \
     --account-name lexiqaitfstate \
     --auth-mode login
   ```

2. **Then import it into Terraform** (optional):
   ```bash
   cd infra/terraform/shared
   terraform init
   terraform import azurerm_resource_group.tfstate /subscriptions/<sub-id>/resourceGroups/lexiqai-tfstate-rg
   terraform import azurerm_storage_account.tfstate /subscriptions/<sub-id>/resourceGroups/lexiqai-tfstate-rg/providers/Microsoft.Storage/storageAccounts/lexiqaitfstate
   # ... etc
   ```

   However, this is more complex and not recommended. The bootstrap approach is simpler.

## Troubleshooting

### Error: "Storage account not found"
- Make sure you completed Phase 1 (created the storage account)
- Verify the storage account name is correct: `lexiqaitfstate`
- Check that you're in the correct Azure subscription

### Error: "Access denied"
- Ensure you're logged into Azure: `az account show`
- Verify you have permissions to create storage accounts
- For GitHub OIDC, ensure the role assignment was created

### Error: "State is locked"
- Another Terraform operation might be running
- Wait a few minutes and try again
- If stuck, check for orphaned leases in Azure Storage

## After Bootstrap

Once the storage account exists and state is migrated:
- All future `terraform init` commands will use the remote backend automatically
- No need for `-backend=false` anymore
- State will be stored in Azure Storage going forward
