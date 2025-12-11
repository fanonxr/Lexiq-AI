# Terraform Configuration Validation Checklist

Use this checklist to verify your Terraform setup is correct before provisioning resources.

## Pre-Flight Checks

### ✅ Azure Authentication

- [ ] Azure CLI installed and working
  ```bash
  az --version
  ```

- [ ] Logged into Azure
  ```bash
  az account show
  ```

- [ ] Active subscription selected
  ```bash
  az account list --output table
  az account set --subscription "<subscription-id>"
  ```

- [ ] Have required roles (Contributor, User Access Administrator)
  ```bash
  az role assignment list --assignee $(az account show --query user.name -o tsv)
  ```

### ✅ Terraform Installation

- [ ] Terraform installed (v1.5.0+)
  ```bash
  terraform version
  ```

- [ ] Terraform in PATH
  ```bash
  which terraform
  ```

### ✅ Configuration Files

- [ ] All required files present:
  - [ ] `main.tf` - Provider and resource group
  - [ ] `variables.tf` - Variable definitions
  - [ ] `outputs.tf` - Output values
  - [ ] `dev.tfvars` - Development variables
  - [ ] `.terraformignore` - Ignore patterns

- [ ] Environment variables set (or update dev.tfvars)
  ```bash
  export TF_VAR_subscription_id=$(az account show --query id -o tsv)
  export TF_VAR_tenant_id=$(az account show --query tenantId -o tsv)
  ```

## Terraform Validation

### ✅ Initialize Terraform

```bash
cd infra/terraform
terraform init
```

**Expected Output:**
- ✅ "Terraform has been successfully initialized!"
- ✅ Azure provider downloaded
- ✅ No errors

**If errors occur:**
- Check internet connection
- Verify Terraform version >= 1.5.0
- Check Azure authentication

### ✅ Validate Configuration

```bash
terraform validate
```

**Expected Output:**
- ✅ "Success! The configuration is valid."

**If errors occur:**
- Check syntax in `.tf` files
- Verify all required variables are defined
- Check variable types match

### ✅ Format Check

```bash
terraform fmt -check -recursive
```

**Expected Output:**
- ✅ No output (files are formatted)
- Or list of files that need formatting

**To auto-format:**
```bash
terraform fmt -recursive
```

### ✅ Plan (Dry Run)

```bash
terraform plan -var-file=dev.tfvars
```

**Expected Output:**
- ✅ Plan shows 1 resource to create (resource group)
- ✅ No errors
- ✅ Resource name: `lexiqai-rg-dev`
- ✅ Location matches your `azure_location`

**Review the plan:**
- Verify resource group name is correct
- Verify location is correct
- Verify tags are applied
- **DO NOT apply if anything looks wrong**

## Resource Group Validation

### ✅ Apply Configuration

```bash
terraform apply -var-file=dev.tfvars
```

**Expected Output:**
- ✅ "Apply complete! Resources: 1 added, 0 changed, 0 destroyed."
- ✅ Resource group created in Azure

### ✅ Verify in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Resource Groups
3. Find `lexiqai-rg-dev`
4. Verify:
   - [ ] Resource group exists
   - [ ] Location is correct
   - [ ] Tags are applied

### ✅ Verify via Azure CLI

```bash
az group show --name lexiqai-rg-dev
```

**Expected Output:**
- ✅ Resource group details
- ✅ Correct location
- ✅ Tags present

### ✅ Verify Terraform State

```bash
terraform show
```

**Expected Output:**
- ✅ Resource group details in state
- ✅ All attributes match Azure

## Troubleshooting

### Common Issues

**"Error: No valid credential sources found"**
- Run `az login`
- Set environment variables: `TF_VAR_subscription_id`, `TF_VAR_tenant_id`

**"Error: Invalid subscription ID"**
- Verify subscription ID: `az account show --query id -o tsv`
- Check subscription is active

**"Error: Insufficient permissions"**
- Verify Contributor role
- Request access from subscription administrator

**"Error: Resource group already exists"**
- Either delete existing resource group
- Or import it: `terraform import azurerm_resource_group.main /subscriptions/.../resourceGroups/lexiqai-rg-dev`

## Next Steps

Once validation is complete:

1. ✅ **Step 3 Complete** - Resource group provisioned
2. ⏭️ **Step 4** - Network Infrastructure (VNet, subnets, NSGs)
3. ⏭️ **Step 9** - Terraform State Management (optional, for remote state)

## Cleanup (If Needed)

To destroy the resource group:

```bash
terraform destroy -var-file=dev.tfvars
```

**⚠️ Warning:** This will delete the resource group and all resources in it!

