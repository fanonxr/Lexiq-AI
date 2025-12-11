#!/bin/bash
# Helper script to get Azure Subscription and Tenant IDs

echo "Getting Azure account information..."
echo ""

SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null)
TENANT_ID=$(az account show --query tenantId -o tsv 2>/dev/null)
ACCOUNT_NAME=$(az account show --query user.name -o tsv 2>/dev/null)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv 2>/dev/null)

if [ -z "$SUBSCRIPTION_ID" ]; then
    echo "❌ Error: Not logged into Azure. Run 'az login' first."
    exit 1
fi

echo "✅ Azure Account Information:"
echo "   Account Name:     $ACCOUNT_NAME"
echo "   Subscription:     $SUBSCRIPTION_NAME"
echo "   Subscription ID:  $SUBSCRIPTION_ID"
echo "   Tenant ID:       $TENANT_ID"
echo ""
echo "📋 Environment Variables:"
echo ""
echo "export TF_VAR_subscription_id=\"$SUBSCRIPTION_ID\""
echo "export TF_VAR_tenant_id=\"$TENANT_ID\""
echo ""
echo "💡 Copy and paste the export commands above to set your environment variables."
