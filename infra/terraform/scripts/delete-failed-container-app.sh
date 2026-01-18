#!/bin/bash
# Script to delete a failed Container App so Terraform can recreate it

set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Source environment variables
if [ -f ../../.env ]; then
    set -a
    source ../../.env
    set +a
fi

# Get variables from tfvars
if [ -f dev.tfvars ]; then
    PROJECT_NAME=$(awk -F'=' '/^project_name/ {print $2}' dev.tfvars | tr -d ' "')
    ENVIRONMENT=$(awk -F'=' '/^environment/ {print $2}' dev.tfvars | tr -d ' "')
else
    echo -e "${RED}Error: dev.tfvars not found${NC}"
    exit 1
fi

RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

# Default to api-core if no argument provided
APP_NAME="${1:-${PROJECT_NAME}-api-core-${ENVIRONMENT}}"

echo -e "${YELLOW}Deleting failed Container App...${NC}"
echo -e "${YELLOW}Resource Group: ${RESOURCE_GROUP}${NC}"
echo -e "${YELLOW}Container App: ${APP_NAME}${NC}"
echo ""

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Check if Container App exists
APP_EXISTS=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "name" -o tsv 2>/dev/null)

if [ -z "$APP_EXISTS" ]; then
    echo -e "${YELLOW}Container App '${APP_NAME}' does not exist in Azure${NC}"
    echo -e "${YELLOW}Checking if it's in Terraform state...${NC}"
    
    # Check Terraform state
    if [ -f "terraform.tfstate" ] || [ -d ".terraform" ]; then
        cd "$(dirname "$0")/.." || exit 1
        if terraform state list 2>/dev/null | grep -q "$APP_NAME"; then
            echo -e "${YELLOW}Found in Terraform state. Removing...${NC}"
            TERRAFORM_ADDRESS=$(terraform state list 2>/dev/null | grep "$APP_NAME" | head -1)
            if [ -n "$TERRAFORM_ADDRESS" ]; then
                echo -e "${YELLOW}Removing from state: ${TERRAFORM_ADDRESS}${NC}"
                terraform state rm "$TERRAFORM_ADDRESS" 2>/dev/null
                echo -e "${GREEN}✓ Removed from Terraform state${NC}"
            fi
        fi
    fi
    exit 0
fi

# Get Container App status
PROVISIONING_STATE=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.provisioningState" -o tsv 2>/dev/null)

echo -e "Provisioning State: ${PROVISIONING_STATE}"
echo ""

if [ "$PROVISIONING_STATE" != "Failed" ]; then
    echo -e "${YELLOW}⚠ Container App is not in 'Failed' state (current: ${PROVISIONING_STATE})${NC}"
    echo -e "${YELLOW}Are you sure you want to delete it?${NC}"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cancelled.${NC}"
        exit 0
    fi
fi

echo -e "${YELLOW}Deleting Container App '${APP_NAME}'...${NC}"

if az containerapp delete --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --yes 2>/dev/null; then
    echo -e "${GREEN}✓ Deleted Container App: ${APP_NAME}${NC}"
    
    # Remove from Terraform state if it exists
    cd "$(dirname "$0")/.." || exit 1
    TERRAFORM_ADDRESS=$(terraform state list 2>/dev/null | grep -E "(api_core|${APP_NAME})" | head -1)
    if [ -n "$TERRAFORM_ADDRESS" ]; then
        echo -e "${YELLOW}Removing from Terraform state: ${TERRAFORM_ADDRESS}${NC}"
        terraform state rm "$TERRAFORM_ADDRESS" 2>/dev/null && echo -e "${GREEN}✓ Removed from Terraform state${NC}" || echo -e "${YELLOW}⚠ Not in Terraform state (or already removed)${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}Deletion complete!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Ensure all required secrets exist in Key Vault"
    echo -e "  2. Run 'make terraform-plan' to verify configuration"
    echo -e "  3. Run 'make terraform-apply' to recreate the Container App"
else
    echo -e "${RED}✗ Failed to delete Container App${NC}"
    exit 1
fi
