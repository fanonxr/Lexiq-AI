#!/bin/bash
# Script to import existing Container Apps into Terraform state

# Don't exit on error - we want to try importing all apps even if some fail
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

echo -e "${YELLOW}Importing Container Apps for project: ${PROJECT_NAME}, environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}Resource Group: ${RESOURCE_GROUP}${NC}"

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

# Check if terraform is initialized
if [ ! -d ".terraform" ]; then
    echo -e "${YELLOW}Warning: Terraform not initialized. Running terraform init...${NC}"
    terraform init
fi

# Get Container Apps Environment ID
CAE_NAME="${PROJECT_NAME}-cae-${ENVIRONMENT}"
CAE_ID=$(az containerapp env show --name "$CAE_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")

if [ -z "$CAE_ID" ]; then
    echo -e "${RED}Error: Container Apps Environment '${CAE_NAME}' not found${NC}"
    exit 1
fi

echo -e "${GREEN}Found Container Apps Environment: ${CAE_NAME}${NC}"

# Check if Container Apps Environment is already in Terraform state
if terraform state list 2>/dev/null | grep -q "module.container_apps.azurerm_container_app_environment.main"; then
    echo -e "${GREEN}✓ Container Apps Environment already in Terraform state${NC}"
else
    echo -e "${YELLOW}⚠ Container Apps Environment not in Terraform state${NC}"
    echo -e "${YELLOW}  You may need to import it first:${NC}"
    echo -e "${YELLOW}  terraform import -var-file=dev.tfvars module.container_apps.azurerm_container_app_environment.main ${CAE_ID}${NC}"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get all Container Apps
CONTAINER_APPS=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, '${PROJECT_NAME}') && contains(name, '${ENVIRONMENT}')].{name:name, id:id}" -o json 2>/dev/null || echo "[]")

if [ -z "$CONTAINER_APPS" ] || [ "$CONTAINER_APPS" == "[]" ]; then
    echo -e "${YELLOW}No Container Apps found to import${NC}"
    exit 0
fi

# Map container app names to Terraform addresses
map_app_name() {
    local APP_NAME=$1
    case "$APP_NAME" in
        *api-core*)
            echo "module.container_apps.azurerm_container_app.api_core"
            ;;
        *cognitive-orch*)
            echo "module.container_apps.azurerm_container_app.cognitive_orch"
            ;;
        *voice-gateway*)
            echo "module.container_apps.azurerm_container_app.voice_gateway"
            ;;
        *document-ingestion*)
            echo "module.container_apps.azurerm_container_app.document_ingestion"
            ;;
        *integration-worker*)
            # Check if it's beat or webhooks
            if [[ "$APP_NAME" == *"beat"* ]] || [[ "$APP_NAME" == *"iw-beat"* ]]; then
                echo "module.container_apps.azurerm_container_app.integration_worker_beat"
            elif [[ "$APP_NAME" == *"webhooks"* ]] || [[ "$APP_NAME" == *"iw-webhooks"* ]]; then
                echo "module.container_apps.azurerm_container_app.integration_worker_webhooks"
            else
                echo "module.container_apps.azurerm_container_app.integration_worker"
            fi
            ;;
        *iw-beat*)
            echo "module.container_apps.azurerm_container_app.integration_worker_beat"
            ;;
        *iw-webhooks*)
            echo "module.container_apps.azurerm_container_app.integration_worker_webhooks"
            ;;
        *redis*)
            echo "module.container_apps.azurerm_container_app.redis"
            ;;
        *qdrant*)
            echo "module.container_apps.azurerm_container_app.qdrant"
            ;;
        *rabbitmq*)
            echo "module.container_apps.azurerm_container_app.rabbitmq"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Import each Container App
IMPORTED=0
FAILED=0

while IFS='|' read -r APP_NAME APP_ID; do
    [ -z "$APP_NAME" ] && continue
    
    TERRAFORM_ADDRESS=$(map_app_name "$APP_NAME")
    
    if [ -z "$TERRAFORM_ADDRESS" ]; then
        echo -e "${YELLOW}⚠ Skipping ${APP_NAME} - no Terraform address mapping found${NC}"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Fix case sensitivity: Azure CLI returns "containerapps" but Terraform expects "containerApps"
    FIXED_APP_ID=$(echo "$APP_ID" | sed 's|/containerapps/|/containerApps/|g')
    
    echo -e "${YELLOW}Importing ${APP_NAME}...${NC}"
    echo -e "  Terraform address: ${TERRAFORM_ADDRESS}"
    echo -e "  Resource ID: ${FIXED_APP_ID}"
    
    # Capture both stdout and stderr to see the actual error
    IMPORT_OUTPUT=$(terraform import -var-file=dev.tfvars "$TERRAFORM_ADDRESS" "$FIXED_APP_ID" 2>&1)
    IMPORT_EXIT_CODE=$?
    
    if [ $IMPORT_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully imported ${APP_NAME}${NC}"
        IMPORTED=$((IMPORTED + 1))
    else
        echo -e "${RED}✗ Failed to import ${APP_NAME}${NC}"
        echo -e "${RED}Error output:${NC}"
        echo "$IMPORT_OUTPUT" | sed 's/^/  /'
        FAILED=$((FAILED + 1))
    fi
    echo ""
done < <(echo "$CONTAINER_APPS" | jq -r '.[] | "\(.name)|\(.id)"')

echo -e "${GREEN}Import complete!${NC}"
echo -e "  Imported: ${IMPORTED}"
echo -e "  Failed: ${FAILED}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Run 'make terraform-plan' to verify the import"
echo -e "  2. Review any differences and update your Terraform configuration if needed"
