#!/bin/bash
# Get GitHub Secrets Values for Terraform CI/CD
# This script outputs the values needed for GitHub repository secrets

set -e

cd "$(dirname "$0")/../shared"

echo "=========================================="
echo "GitHub Secrets for Terraform CI/CD"
echo "=========================================="
echo ""
echo "Copy these values to GitHub:"
echo "Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "----------------------------------------"
echo ""

# Check if Terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "⚠️  Terraform not initialized. Running terraform init..."
    terraform init > /dev/null 2>&1
fi

# Get values
echo "1. AZURE_CLIENT_ID"
echo "   Value: $(terraform output -raw github_oidc_application_id 2>/dev/null || echo 'NOT FOUND - Run terraform apply first')"
echo ""

echo "2. AZURE_TENANT_ID"
echo "   Value: $(terraform output -raw github_oidc_tenant_id 2>/dev/null || echo 'NOT FOUND - Run terraform apply first')"
echo ""

echo "3. AZURE_SUBSCRIPTION_ID"
SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null || echo "NOT FOUND - Run 'az login' first")
echo "   Value: $SUBSCRIPTION_ID"
echo ""

echo "4. TF_STATE_RG"
echo "   Value: $(terraform output -raw tfstate_resource_group_name 2>/dev/null || echo 'NOT FOUND - Run terraform apply first')"
echo ""

echo "5. TF_STATE_STORAGE_ACCOUNT"
echo "   Value: $(terraform output -raw tfstate_storage_account_name 2>/dev/null || echo 'NOT FOUND - Run terraform apply first')"
echo ""

echo "6. TF_STATE_CONTAINER"
echo "   Value: $(terraform output -raw tfstate_container_name 2>/dev/null || echo 'NOT FOUND - Run terraform apply first')"
echo ""

echo "----------------------------------------"
echo ""
echo "✅ Copy each value above to GitHub Secrets"
echo ""
echo "For detailed instructions, see:"
echo "  docs/terraform/GITHUB_SECRETS_SETUP.md"
