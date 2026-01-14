#!/bin/bash
# Quick script to import Container Apps Environment into Terraform state

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to terraform directory
cd "$(dirname "$0")/.."

# Source .env if it exists
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
fi

# Get project name and environment from tfvars
PROJECT_NAME=$(awk -F'=' '/^[[:space:]]*project_name[[:space:]]*=/ {gsub(/[" ]/, "", $2); print $2}' dev.tfvars 2>/dev/null || echo "lexiqai")
ENVIRONMENT=$(awk -F'=' '/^[[:space:]]*environment[[:space:]]*=/ {gsub(/[" ]/, "", $2); print $2}' dev.tfvars 2>/dev/null || echo "dev")
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"
CAE_NAME="${PROJECT_NAME}-cae-${ENVIRONMENT}"

echo -e "${YELLOW}Importing Container Apps Environment: ${CAE_NAME}${NC}"
echo ""

# Get the resource ID
CAE_ID=$(az containerapp env show --name "$CAE_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")

if [ -z "$CAE_ID" ]; then
    echo -e "${RED}Error: Container Apps Environment '${CAE_NAME}' not found${NC}"
    echo "Please verify the name and resource group are correct."
    exit 1
fi

echo -e "${GREEN}Found Container Apps Environment:${NC}"
echo "  Name: ${CAE_NAME}"
echo "  ID: ${CAE_ID}"
echo ""

# Import into Terraform state
echo -e "${YELLOW}Importing into Terraform state...${NC}"
terraform import -var-file=dev.tfvars \
  module.container_apps.azurerm_container_app_environment.main \
  "$CAE_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Successfully imported Container Apps Environment${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Run 'make terraform-plan' to verify the import"
    echo "2. If there are differences, Terraform will show what needs to be updated"
else
    echo ""
    echo -e "${RED}✗ Failed to import Container Apps Environment${NC}"
    exit 1
fi
