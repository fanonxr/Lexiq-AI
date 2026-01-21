#!/bin/bash
# Grant current user access to Terraform state storage account

set -e

STORAGE_ACCOUNT="lexiqaitfstate"
RESOURCE_GROUP="lexiqai-tfstate-rg"
ROLE="Storage Blob Data Contributor"

echo "🔐 Granting access to Terraform state storage account..."

# Get current user's object ID
CURRENT_USER=$(az account show --query user.name -o tsv)
echo "Current user: $CURRENT_USER"

# Get storage account resource ID
STORAGE_ACCOUNT_ID=$(az storage account show \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query id -o tsv)

if [ -z "$STORAGE_ACCOUNT_ID" ]; then
    echo "❌ Error: Storage account '$STORAGE_ACCOUNT' not found in resource group '$RESOURCE_GROUP'"
    exit 1
fi

echo "Storage account ID: $STORAGE_ACCOUNT_ID"
echo ""

# Check if role assignment already exists
EXISTING=$(az role assignment list \
  --assignee "$CURRENT_USER" \
  --scope "$STORAGE_ACCOUNT_ID" \
  --role "$ROLE" \
  --query "[].id" -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING" ]; then
    echo "✅ Role assignment already exists"
    echo "   You already have '$ROLE' role on the storage account"
else
    echo "Creating role assignment..."
    az role assignment create \
      --assignee "$CURRENT_USER" \
      --role "$ROLE" \
      --scope "$STORAGE_ACCOUNT_ID" \
      --output table
    
    echo ""
    echo "✅ Access granted! It may take a few moments to propagate."
    echo "   Wait 10-30 seconds before trying the command again."
fi

echo ""
echo "You can now verify access with:"
echo "  az storage blob list \\"
echo "    --container-name terraform-state \\"
echo "    --account-name $STORAGE_ACCOUNT \\"
echo "    --auth-mode login"
