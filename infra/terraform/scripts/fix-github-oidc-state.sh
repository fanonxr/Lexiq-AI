#!/bin/bash
# Script to fix GitHub OIDC application state issues

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

APP_DISPLAY_NAME="${PROJECT_NAME}-github-actions-${ENVIRONMENT}"

echo -e "${YELLOW}Checking GitHub OIDC Application State${NC}"
echo ""

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Get the actual application from Azure
echo -e "${YELLOW}1. Finding application in Azure AD...${NC}"
APP_OBJECT_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].id" -o tsv 2>/dev/null)
APP_CLIENT_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv 2>/dev/null)

if [ -z "$APP_OBJECT_ID" ] || [ "$APP_OBJECT_ID" == "null" ]; then
    echo -e "${RED}✗ Application '${APP_DISPLAY_NAME}' not found in Azure AD${NC}"
    echo -e "${YELLOW}  You need to create it first with 'terraform apply'${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found application in Azure:${NC}"
echo -e "  Display Name: ${APP_DISPLAY_NAME}"
echo -e "  Object ID: ${APP_OBJECT_ID}"
echo -e "  Client ID: ${APP_CLIENT_ID}"
echo ""

# Check Terraform state
echo -e "${YELLOW}2. Checking Terraform state...${NC}"
if terraform state list 2>/dev/null | grep -q "module.github_oidc\[0\].azuread_application.github_actions"; then
    echo -e "${GREEN}✓ Application is in Terraform state${NC}"
    
    # Show the current state
    echo -e "${YELLOW}  Current state details:${NC}"
    terraform state show 'module.github_oidc[0].azuread_application.github_actions' 2>/dev/null | grep -E "(id|object_id|client_id)" || true
    
    # Check if the object ID matches
    STATE_OBJECT_ID=$(terraform state show 'module.github_oidc[0].azuread_application.github_actions' 2>/dev/null | grep -E "^id\s*=" | awk '{print $3}' | tr -d '"' || echo "")
    
    if [ -n "$STATE_OBJECT_ID" ] && [ "$STATE_OBJECT_ID" != "$APP_OBJECT_ID" ]; then
        echo -e "${RED}✗ Object ID mismatch!${NC}"
        echo -e "  State has: ${STATE_OBJECT_ID}"
        echo -e "  Azure has: ${APP_OBJECT_ID}"
        echo -e "${YELLOW}  Removing from state to re-import...${NC}"
        terraform state rm 'module.github_oidc[0].azuread_application.github_actions' 2>/dev/null || true
        terraform state rm 'module.github_oidc[0].azuread_service_principal.github_actions' 2>/dev/null || true
        terraform state rm 'module.github_oidc[0].azuread_application_federated_identity_credential.github_actions' 2>/dev/null || true
        echo -e "${YELLOW}  Now run the import script again${NC}"
    else
        echo -e "${GREEN}✓ Object IDs match${NC}"
    fi
else
    echo -e "${YELLOW}  Application NOT in Terraform state${NC}"
    echo -e "${YELLOW}  You need to import it${NC}"
fi

echo ""
echo -e "${YELLOW}3. Recommended next steps:${NC}"
if terraform state list 2>/dev/null | grep -q "module.github_oidc\[0\].azuread_application.github_actions"; then
    echo -e "  1. Run 'terraform plan -var-file=dev.tfvars' to see what Terraform wants to change"
    echo -e "  2. If there are issues, the application might need to be re-imported"
else
    echo -e "  1. Run 'make terraform-import-github-oidc' to import the application"
    echo -e "  2. Then run 'terraform plan -var-file=dev.tfvars' to verify"
fi
