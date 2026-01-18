#!/bin/bash
# Script to import existing GitHub OIDC application and related resources into Terraform state

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

echo -e "${YELLOW}Importing GitHub OIDC Application into Terraform State${NC}"
echo -e "Project: ${PROJECT_NAME}"
echo -e "Environment: ${ENVIRONMENT}"
echo ""

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Check if we're in the terraform directory
if [ ! -f "main.tf" ]; then
    echo -e "${RED}Error: This script must be run from the infra/terraform directory${NC}"
    exit 1
fi

APP_DISPLAY_NAME="${PROJECT_NAME}-github-actions-${ENVIRONMENT}"

echo -e "${YELLOW}1. Finding application in Azure AD...${NC}"
APP_OBJECT_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].id" -o tsv 2>/dev/null)

if [ -z "$APP_OBJECT_ID" ] || [ "$APP_OBJECT_ID" == "null" ]; then
    echo -e "${RED}✗ Application '${APP_DISPLAY_NAME}' not found in Azure AD${NC}"
    echo -e "${YELLOW}   You may need to create it first with 'terraform apply'${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found application: ${APP_OBJECT_ID}${NC}"

APP_CLIENT_ID=$(az ad app list --display-name "$APP_DISPLAY_NAME" --query "[0].appId" -o tsv 2>/dev/null)
echo -e "  Client ID: ${APP_CLIENT_ID}"

# Ensure Terraform configuration is evaluated first
echo -e "${YELLOW}  Initializing Terraform and evaluating configuration...${NC}"
terraform init -backend=false >/dev/null 2>&1
terraform validate >/dev/null 2>&1

# Check if github_repository is set
GITHUB_REPO=$(awk -F'=' '/^github_repository/ {print $2}' dev.tfvars | tr -d ' "')
if [ -z "$GITHUB_REPO" ] || [ "$GITHUB_REPO" == "" ]; then
    echo -e "${RED}✗ Error: github_repository is not set in dev.tfvars${NC}"
    echo -e "${YELLOW}  The github_oidc module requires github_repository to be set${NC}"
    exit 1
fi

echo -e "${GREEN}✓ GitHub repository configured: ${GITHUB_REPO}${NC}"

# Check if application is already in Terraform state
if terraform state list 2>/dev/null | grep -q "module.github_oidc\[0\].azuread_application.github_actions"; then
    echo -e "${YELLOW}  Application already in Terraform state. Removing first...${NC}"
    terraform state rm 'module.github_oidc[0].azuread_application.github_actions' 2>/dev/null || true
    terraform state rm 'module.github_oidc[0].azuread_service_principal.github_actions' 2>/dev/null || true
    terraform state rm 'module.github_oidc[0].azuread_application_federated_identity_credential.github_actions' 2>/dev/null || true
fi

echo ""
echo -e "${YELLOW}2. Importing Azure AD Application...${NC}"
echo -e "   Resource: module.github_oidc[0].azuread_application.github_actions"
echo -e "   Object ID: ${APP_OBJECT_ID}"
echo -e "   Client ID: ${APP_CLIENT_ID}"

# Try different import ID formats
# Some provider versions might expect /applications/{object_id} format
IMPORT_SUCCESS=false

# Try 1: /applications/{object_id} format (as error message suggests)
echo -e "${YELLOW}  Attempting import with /applications/{object_id} format...${NC}"
if terraform import -var-file=dev.tfvars 'module.github_oidc[0].azuread_application.github_actions' "/applications/${APP_OBJECT_ID}" 2>&1 | tee /tmp/import_output.txt; then
    echo -e "${GREEN}✓ Successfully imported application with /applications/{object_id} format${NC}"
    IMPORT_SUCCESS=true
else
    # Try 2: Just the object ID (standard format)
    echo -e "${YELLOW}  That didn't work. Trying with just object ID...${NC}"
    if terraform import -var-file=dev.tfvars 'module.github_oidc[0].azuread_application.github_actions' "$APP_OBJECT_ID" 2>&1 | tee /tmp/import_output.txt; then
        echo -e "${GREEN}✓ Successfully imported application with object ID${NC}"
        IMPORT_SUCCESS=true
    else
        # Try 3: Using -target flag
        echo -e "${YELLOW}  That didn't work. Trying with -target flag...${NC}"
        if terraform import -var-file=dev.tfvars -target='module.github_oidc[0].azuread_application.github_actions' 'module.github_oidc[0].azuread_application.github_actions' "/applications/${APP_OBJECT_ID}" 2>&1 | tee /tmp/import_output.txt; then
            echo -e "${GREEN}✓ Successfully imported application with -target and /applications format${NC}"
            IMPORT_SUCCESS=true
        else
            # Try 4: -target with just object ID
            echo -e "${YELLOW}  That didn't work. Trying -target with object ID...${NC}"
            if terraform import -var-file=dev.tfvars -target='module.github_oidc[0].azuread_application.github_actions' 'module.github_oidc[0].azuread_application.github_actions' "$APP_OBJECT_ID" 2>&1 | tee /tmp/import_output.txt; then
                echo -e "${GREEN}✓ Successfully imported application with -target and object ID${NC}"
                IMPORT_SUCCESS=true
            fi
        fi
    fi
fi

if [ "$IMPORT_SUCCESS" = false ]; then
    echo -e "${RED}✗ Failed to import application with all attempted formats${NC}"
    echo -e "${YELLOW}  Last error output:${NC}"
    cat /tmp/import_output.txt 2>/dev/null || true
    echo -e ""
    echo -e "${YELLOW}  Manual import commands to try:${NC}"
    echo -e "  1. /applications format: terraform import -var-file=dev.tfvars 'module.github_oidc[0].azuread_application.github_actions' '/applications/${APP_OBJECT_ID}'"
    echo -e "  2. Object ID format: terraform import -var-file=dev.tfvars 'module.github_oidc[0].azuread_application.github_actions' '${APP_OBJECT_ID}'"
    exit 1
fi

echo ""
echo -e "${YELLOW}3. Finding Service Principal...${NC}"
SP_OBJECT_ID=$(az ad sp list --filter "appId eq '${APP_CLIENT_ID}'" --query "[0].id" -o tsv 2>/dev/null)

if [ -n "$SP_OBJECT_ID" ] && [ "$SP_OBJECT_ID" != "null" ]; then
    echo -e "${GREEN}✓ Found service principal: ${SP_OBJECT_ID}${NC}"
    echo -e "${YELLOW}  Importing Service Principal...${NC}"
    if terraform import -var-file=dev.tfvars 'module.github_oidc[0].azuread_service_principal.github_actions' "$SP_OBJECT_ID" 2>&1; then
        echo -e "${GREEN}✓ Successfully imported service principal${NC}"
    else
        echo -e "${YELLOW}  Warning: Failed to import service principal (may need to be created)${NC}"
    fi
else
    echo -e "${YELLOW}  Service principal not found (will be created on next apply)${NC}"
fi

echo ""
echo -e "${YELLOW}4. Checking for Federated Identity Credentials...${NC}"
FIC_LIST=$(az ad app federated-credential list --id "$APP_OBJECT_ID" --query "[].{id:id, displayName:displayName}" -o json 2>/dev/null)

if [ -n "$FIC_LIST" ] && [ "$FIC_LIST" != "[]" ]; then
    FIC_COUNT=$(echo "$FIC_LIST" | jq '. | length' 2>/dev/null || echo "0")
    if [ "$FIC_COUNT" -gt 0 ]; then
        echo -e "${GREEN}  Found ${FIC_COUNT} federated identity credential(s)${NC}"
        # Note: Federated identity credentials are tricky to import as they don't have a simple ID format
        # They're typically managed by Terraform, so we'll let Terraform recreate them if needed
        echo -e "${YELLOW}  Note: Federated identity credentials will be managed by Terraform${NC}"
        echo -e "${YELLOW}  If there are existing ones, you may need to remove them manually or let Terraform recreate them${NC}"
    fi
else
    echo -e "${YELLOW}  No federated identity credentials found (will be created on next apply)${NC}"
fi

echo ""
echo -e "${GREEN}✓ Import complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Run 'terraform plan' to see what changes Terraform wants to make"
echo -e "  2. If federated identity credentials need to be recreated, Terraform will handle it"
echo -e "  3. Run 'terraform apply' to sync any remaining resources"
