#!/bin/bash
# Script to check GitHub OIDC application and federated identity credential status

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
    GITHUB_REPO=$(awk -F'=' '/^github_repository/ {print $2}' dev.tfvars | tr -d ' "')
else
    echo -e "${RED}Error: dev.tfvars not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Checking GitHub OIDC Application Status${NC}"
echo -e "Project: ${PROJECT_NAME}"
echo -e "Environment: ${ENVIRONMENT}"
echo -e "GitHub Repository: ${GITHUB_REPO}"
echo ""

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

APP_DISPLAY_NAME="${PROJECT_NAME}-github-actions-${ENVIRONMENT}"

echo -e "${YELLOW}1. Checking if application exists in Azure AD...${NC}"
APP_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv 2>/dev/null)

if [ -z "$APP_ID" ] || [ "$APP_ID" == "null" ]; then
    echo -e "${RED}✗ Application '${APP_DISPLAY_NAME}' not found in Azure AD${NC}"
    echo -e "${YELLOW}   This means the application needs to be created by Terraform.${NC}"
else
    echo -e "${GREEN}✓ Application found: ${APP_ID}${NC}"
    
    APP_OBJECT_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].id" -o tsv 2>/dev/null)
    echo -e "  Object ID: ${APP_OBJECT_ID}"
    
    echo ""
    echo -e "${YELLOW}2. Checking federated identity credentials...${NC}"
    FIC_LIST=$(az ad app federated-credential list --id "$APP_OBJECT_ID" --query "[].{displayName:displayName, subject:subject}" -o json 2>/dev/null)
    
    if [ -z "$FIC_LIST" ] || [ "$FIC_LIST" == "[]" ]; then
        echo -e "${YELLOW}  No federated identity credentials found${NC}"
    else
        echo -e "${GREEN}  Found federated identity credentials:${NC}"
        echo "$FIC_LIST" | jq -r '.[] | "  - \(.displayName): \(.subject)"' 2>/dev/null || echo "$FIC_LIST"
    fi
fi

echo ""
echo -e "${YELLOW}3. Checking Terraform state...${NC}"
if [ -f terraform.tfstate ] || [ -f .terraform/terraform.tfstate ]; then
    if terraform state list 2>/dev/null | grep -q "module.github_oidc"; then
        echo -e "${GREEN}✓ GitHub OIDC module resources found in Terraform state${NC}"
        terraform state list 2>/dev/null | grep "module.github_oidc" | while read -r resource; do
            echo "  - $resource"
        done
    else
        echo -e "${YELLOW}  No GitHub OIDC resources in Terraform state${NC}"
    fi
else
    echo -e "${YELLOW}  Terraform state file not found${NC}"
fi

echo ""
echo -e "${YELLOW}Recommendations:${NC}"
if [ -z "$APP_ID" ] || [ "$APP_ID" == "null" ]; then
    echo -e "  1. Run 'terraform apply' to create the application"
    echo -e "  2. If it fails, check Azure AD permissions"
else
    echo -e "  1. If Terraform state is out of sync, run:"
    echo -e "     terraform import module.github_oidc[0].azuread_application.github_actions $APP_OBJECT_ID"
    echo -e "  2. Then run 'terraform apply' again"
fi
