# Importing Existing Azure Resources

If you have existing resources in Azure that were created outside of Terraform (or the state was lost), you need to import them.

## Current Situation

The VNet `lexiqai-vnet-dev` exists in Azure (westus) but not in Terraform state.

## Option 1: Import Existing Resources (Recommended if you want to keep them)

```bash
cd infra/terraform

# Get the VNet resource ID
VNET_ID=$(az network vnet show --resource-group lexiqai-rg-dev --name lexiqai-vnet-dev --query id -o tsv)

# Import the VNet
terraform import -var-file=dev.tfvars module.network.azurerm_virtual_network.main $VNET_ID

# Import subnets
SUBNET_COMPUTE_ID=$(az network vnet subnet show --resource-group lexiqai-rg-dev --vnet-name lexiqai-vnet-dev --name lexiqai-compute-subnet-dev --query id -o tsv)
terraform import -var-file=dev.tfvars module.network.azurerm_subnet.compute $SUBNET_COMPUTE_ID

SUBNET_DATA_ID=$(az network vnet subnet show --resource-group lexiqai-rg-dev --vnet-name lexiqai-vnet-dev --name lexiqai-data-subnet-dev --query id -o tsv)
terraform import -var-file=dev.tfvars module.network.azurerm_subnet.data $SUBNET_DATA_ID

SUBNET_PE_ID=$(az network vnet subnet show --resource-group lexiqai-rg-dev --vnet-name lexiqai-vnet-dev --name lexiqai-private-endpoint-subnet-dev --query id -o tsv)
terraform import -var-file=dev.tfvars module.network.azurerm_subnet.private_endpoint $SUBNET_PE_ID
```

## Option 2: Destroy and Recreate (Easier for dev environment)

If you're okay with recreating the VNet:

```bash
cd infra/terraform

# Delete the VNet from Azure (this will delete all subnets too)
az network vnet delete --resource-group lexiqai-rg-dev --name lexiqai-vnet-dev

# Then apply Terraform to create everything
make terraform-apply
```

## Option 3: Let Terraform Handle It (If state is truly empty)

If the state file is completely empty and you want Terraform to manage everything:

```bash
cd infra/terraform

# Terraform will detect the VNet exists and may need adjustment
# You might need to rename the VNet in Azure first, or use terraform import
```

## Recommended Approach for Dev

Since you're in development, **Option 2** (destroy and recreate) is usually easiest and ensures everything is in sync.

