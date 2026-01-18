#!/bin/bash
# Script to remove old environment-specific ACR from Terraform state and optionally delete from Azure
# Usage: ./cleanup-old-acr.sh <environment> [--delete-from-azure]
# Example: ./cleanup-old-acr.sh dev
# Example: ./cleanup-old-acr.sh dev --delete-from-azure

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
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"
ACR_NAME="${PROJECT_NAME}acr${ENVIRONMENT}"

echo -e "${GREEN}=== Old ACR Cleanup Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "ACR Name: $ACR_NAME"
echo "Delete from Azure: $DELETE_FROM_AZURE"
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

# Verify ACR exists in Azure
echo -e "${YELLOW}Checking if ACR exists in Azure...${NC}"
if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
  echo -e "${GREEN}✓ ACR found in Azure${NC}"
else
  echo -e "${YELLOW}⚠ ACR not found in Azure (may already be deleted)${NC}"
fi

# Check if ACR is in Terraform state
echo -e "${YELLOW}Checking Terraform state...${NC}"
if terraform state list 2>/dev/null | grep -q "azurerm_container_registry.main"; then
  echo -e "${GREEN}✓ ACR found in Terraform state${NC}"
  
  # Remove from Terraform state
  echo ""
  echo -e "${YELLOW}Removing ACR from Terraform state...${NC}"
  if terraform state rm 'azurerm_container_registry.main' 2>/dev/null; then
    echo -e "${GREEN}✓ Removed from Terraform state${NC}"
  else
    echo -e "${RED}✗ Failed to remove from Terraform state${NC}"
    echo "You may need to run this manually:"
    echo "  cd $TERRAFORM_DIR"
    echo "  terraform state rm 'azurerm_container_registry.main'"
    exit 1
  fi
else
  echo -e "${YELLOW}⚠ ACR not found in Terraform state (may already be removed)${NC}"
fi

# Remove ACR role assignments from state (if they exist)
echo ""
echo -e "${YELLOW}Checking for ACR role assignments in Terraform state...${NC}"
if terraform state list 2>/dev/null | grep -q "azurerm_role_assignment.acr_pull"; then
  echo -e "${YELLOW}Removing ACR pull role assignment from state...${NC}"
  terraform state rm 'azurerm_role_assignment.acr_pull' 2>/dev/null || true
fi

if terraform state list 2>/dev/null | grep -q "azurerm_role_assignment.acr_push"; then
  echo -e "${YELLOW}Removing ACR push role assignment from state...${NC}"
  terraform state rm 'azurerm_role_assignment.acr_push' 2>/dev/null || true
fi

# Delete from Azure if requested
if [ "$DELETE_FROM_AZURE" == "true" ]; then
  echo ""
  echo -e "${YELLOW}Deleting ACR from Azure...${NC}"
  if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    read -p "Are you sure you want to delete ACR '$ACR_NAME'? This cannot be undone! (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
      if az acr delete --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --yes; then
        echo -e "${GREEN}✓ ACR deleted from Azure${NC}"
      else
        echo -e "${RED}✗ Failed to delete ACR from Azure${NC}"
        exit 1
      fi
    else
      echo -e "${YELLOW}Cancelled deletion${NC}"
    fi
  else
    echo -e "${YELLOW}⚠ ACR not found in Azure (may already be deleted)${NC}"
  fi
else
  echo ""
  echo -e "${YELLOW}⚠ ACR still exists in Azure${NC}"
  echo "To delete it, run:"
  echo "  az acr delete --name $ACR_NAME --resource-group $RESOURCE_GROUP --yes"
fi

echo ""
echo -e "${GREEN}=== Cleanup Summary ===${NC}"
echo "✓ ACR removed from Terraform state"
if [ "$DELETE_FROM_AZURE" == "true" ]; then
  echo "✓ ACR deleted from Azure"
else
  echo "⚠ ACR still exists in Azure (use --delete-from-azure to delete)"
fi
echo ""
echo "Next steps:"
echo "1. Verify Terraform code has ACR resource commented out (already done in Phase 3)"
echo "2. Run 'terraform plan' to verify no changes needed"
echo "3. Run 'terraform apply' to ensure state is consistent"
