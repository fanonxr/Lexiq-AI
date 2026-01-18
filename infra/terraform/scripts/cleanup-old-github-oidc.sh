#!/bin/bash
# Script to remove old environment-specific GitHub OIDC app from Terraform state and optionally delete from Azure AD
# Usage: ./cleanup-old-github-oidc.sh <environment> [--delete-from-azure]
# Example: ./cleanup-old-github-oidc.sh dev
# Example: ./cleanup-old-github-oidc.sh dev --delete-from-azure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
  echo -e "${RED}Error: Environment is required${NC}"
  echo "Usage: $0 <environment> [--delete-from-azure]"
  echo "Example: $0 dev"
  echo "Example: $0 dev --delete-from-azure"
  exit 1
fi

ENVIRONMENT=$1
DELETE_FROM_AZURE=false
if [ "$2" == "--delete-from-azure" ]; then
  DELETE_FROM_AZURE=true
fi

PROJECT_NAME="lexiqai"
APP_DISPLAY_NAME="${PROJECT_NAME}-github-actions-${ENVIRONMENT}"

echo -e "${GREEN}=== Old GitHub OIDC Cleanup Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "App Display Name: $APP_DISPLAY_NAME"
echo "Delete from Azure AD: $DELETE_FROM_AZURE"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
  echo -e "${RED}Error: Azure CLI is not installed${NC}"
  exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
  echo -e "${RED}Error: Not logged in to Azure. Run 'az login' first.${NC}"
  exit 1
fi

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
  echo -e "${RED}Error: Terraform is not installed${NC}"
  exit 1
fi

# Change to Terraform directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/.."
cd "$TERRAFORM_DIR"

# Find the application in Azure AD
echo -e "${YELLOW}Searching for GitHub OIDC app in Azure AD...${NC}"
APP_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv 2>/dev/null || echo "")

if [ -n "$APP_ID" ] && [ "$APP_ID" != "null" ]; then
  echo -e "${GREEN}✓ Found app with ID: $APP_ID${NC}"
  APP_OBJECT_ID=$(az ad app show --id "$APP_ID" --query "id" -o tsv 2>/dev/null || echo "")
else
  echo -e "${YELLOW}⚠ App not found in Azure AD (may already be deleted)${NC}"
  APP_ID=""
  APP_OBJECT_ID=""
fi

# Check if GitHub OIDC module is in Terraform state
echo ""
echo -e "${YELLOW}Checking Terraform state...${NC}"
MODULE_IN_STATE=false

if terraform state list 2>/dev/null | grep -q "module.github_oidc"; then
  MODULE_IN_STATE=true
  echo -e "${GREEN}✓ GitHub OIDC module found in Terraform state${NC}"
  
  # Remove federated identity credential from state
  if terraform state list 2>/dev/null | grep -q "module.github_oidc.*azuread_application_federated_identity_credential"; then
    echo -e "${YELLOW}Removing federated identity credential from state...${NC}"
    terraform state list 2>/dev/null | grep "module.github_oidc.*azuread_application_federated_identity_credential" | while read -r resource; do
      terraform state rm "$resource" 2>/dev/null || true
    done
  fi
  
  # Remove service principal from state
  if terraform state list 2>/dev/null | grep -q "module.github_oidc.*azuread_service_principal"; then
    echo -e "${YELLOW}Removing service principal from state...${NC}"
    terraform state rm 'module.github_oidc[0].azuread_service_principal.github_actions' 2>/dev/null || true
  fi
  
  # Remove application from state
  if terraform state list 2>/dev/null | grep -q "module.github_oidc.*azuread_application"; then
    echo -e "${YELLOW}Removing application from state...${NC}"
    terraform state rm 'module.github_oidc[0].azuread_application.github_actions' 2>/dev/null || true
  fi
  
  # Remove entire module from state
  echo -e "${YELLOW}Removing GitHub OIDC module from state...${NC}"
  if terraform state rm 'module.github_oidc[0]' 2>/dev/null; then
    echo -e "${GREEN}✓ Removed module from Terraform state${NC}"
  else
    echo -e "${YELLOW}⚠ Module may have dependencies, removing individual resources...${NC}"
  fi
else
  echo -e "${YELLOW}⚠ GitHub OIDC module not found in Terraform state (may already be removed)${NC}"
fi

# Delete from Azure AD if requested
if [ "$DELETE_FROM_AZURE" == "true" ] && [ -n "$APP_ID" ]; then
  echo ""
  echo -e "${YELLOW}Deleting app from Azure AD...${NC}"
  read -p "Are you sure you want to delete app '$APP_DISPLAY_NAME'? This cannot be undone! (yes/no): " confirm
  if [ "$confirm" == "yes" ]; then
    if az ad app delete --id "$APP_ID"; then
      echo -e "${GREEN}✓ App deleted from Azure AD${NC}"
    else
      echo -e "${RED}✗ Failed to delete app from Azure AD${NC}"
      exit 1
    fi
  else
    echo -e "${YELLOW}Cancelled deletion${NC}"
  fi
elif [ "$DELETE_FROM_AZURE" == "true" ] && [ -z "$APP_ID" ]; then
  echo -e "${YELLOW}⚠ App not found in Azure AD (may already be deleted)${NC}"
fi

echo ""
echo -e "${GREEN}=== Cleanup Summary ===${NC}"
if [ "$MODULE_IN_STATE" == "true" ]; then
  echo "✓ GitHub OIDC module removed from Terraform state"
else
  echo "⚠ GitHub OIDC module not found in Terraform state (may already be removed)"
fi

if [ "$DELETE_FROM_AZURE" == "true" ] && [ -n "$APP_ID" ]; then
  echo "✓ App deleted from Azure AD"
elif [ "$DELETE_FROM_AZURE" == "true" ]; then
  echo "⚠ App not found in Azure AD (may already be deleted)"
else
  echo "⚠ App still exists in Azure AD (use --delete-from-azure to delete)"
  if [ -n "$APP_ID" ]; then
    echo "  App ID: $APP_ID"
    echo "  To delete manually: az ad app delete --id $APP_ID"
  fi
fi

echo ""
echo "Next steps:"
echo "1. Verify Terraform code has GitHub OIDC module commented out (already done in Phase 3)"
echo "2. Run 'terraform plan' to verify no changes needed"
echo "3. Run 'terraform apply' to ensure state is consistent"
