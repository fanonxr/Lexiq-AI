#!/bin/bash
# Script to import existing Azure resources into Terraform state
# This discovers resources in the resource group and generates import commands

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get environment from argument or default to dev
ENVIRONMENT=${1:-dev}
VAR_FILE="${ENVIRONMENT}.tfvars"

# Check if var file exists
if [ ! -f "$VAR_FILE" ]; then
    echo -e "${RED}Error: ${VAR_FILE} not found${NC}"
    echo "Usage: $0 [dev|staging|prod]"
    exit 1
fi

# Source variables from tfvars to get project name and location
# Handle both quoted and unquoted values, with or without spaces around =
PROJECT_NAME=$(awk -F'=' '/^[[:space:]]*project_name[[:space:]]*=/ {gsub(/[" ]/, "", $2); print $2}' "$VAR_FILE" | head -1 || echo "lexiqai")
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

# Debug output (can be removed later)
echo -e "${YELLOW}Parsed project_name: '${PROJECT_NAME}'${NC}"
echo -e "${YELLOW}Resource group: '${RESOURCE_GROUP}'${NC}"

echo -e "${GREEN}Discovering resources in resource group: ${RESOURCE_GROUP}${NC}"

# Check if logged into Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure CLI${NC}"
    echo "Please run: az login"
    exit 1
fi

# Check if resource group exists
RG_EXISTS=$(az group show --name "$RESOURCE_GROUP" --query "name" -o tsv 2>&1)
if [ $? -ne 0 ] || [ -z "$RG_EXISTS" ]; then
    echo -e "${RED}Error: Resource group '${RESOURCE_GROUP}' not found${NC}"
    echo ""
    echo "Available resource groups:"
    az group list --query "[].name" -o table 2>/dev/null || echo "  (Unable to list resource groups)"
    echo ""
    echo "Please verify:"
    echo "  1. You're logged in: az login"
    echo "  2. You're using the correct subscription: az account show"
    echo "  3. The resource group name is correct: ${RESOURCE_GROUP}"
    exit 1
fi

# Create import commands file
IMPORT_FILE="import-commands-${ENVIRONMENT}.sh"
echo "#!/bin/bash" > "$IMPORT_FILE"
echo "# Auto-generated import commands for ${ENVIRONMENT} environment" >> "$IMPORT_FILE"
echo "# Generated on $(date)" >> "$IMPORT_FILE"
echo "" >> "$IMPORT_FILE"
echo "set -e" >> "$IMPORT_FILE"
echo "" >> "$IMPORT_FILE"
echo "cd \$(dirname \$0)" >> "$IMPORT_FILE"
echo "" >> "$IMPORT_FILE"

IMPORT_COUNT=0

# Function to add import command
add_import() {
    local RESOURCE_TYPE=$1
    local RESOURCE_NAME=$2
    local AZURE_ID=$3
    local TERRAFORM_ADDRESS=$4
    
    echo "echo \"Importing ${TERRAFORM_ADDRESS}...\"" >> "$IMPORT_FILE"
    # Source .env if it exists (for TF_VAR_* environment variables)
    # The import script runs from infra/terraform directory, so .env is at ../.env
    echo "if [ -f ../.env ]; then set -a; source ../.env; set +a; fi" >> "$IMPORT_FILE"
    echo "terraform import -var-file=${VAR_FILE} ${TERRAFORM_ADDRESS} \"${AZURE_ID}\" || echo \"  ⚠️  Failed to import ${TERRAFORM_ADDRESS}\"" >> "$IMPORT_FILE"
    echo "" >> "$IMPORT_FILE"
    ((IMPORT_COUNT++))
}

# Import Resource Group
echo -e "${YELLOW}Checking Resource Group...${NC}"
RG_ID=$(az group show --name "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$RG_ID" ]; then
    add_import "azurerm_resource_group" "main" "$RG_ID" "azurerm_resource_group.main"
    echo -e "${GREEN}✓ Found Resource Group${NC}"
fi

# Import Virtual Network
echo -e "${YELLOW}Checking Virtual Network...${NC}"
VNET_NAME="${PROJECT_NAME}-vnet-${ENVIRONMENT}"
VNET_ID=$(az network vnet show --resource-group "$RESOURCE_GROUP" --name "$VNET_NAME" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$VNET_ID" ]; then
    add_import "azurerm_virtual_network" "$VNET_NAME" "$VNET_ID" "module.network.azurerm_virtual_network.main"
    echo -e "${GREEN}✓ Found Virtual Network: ${VNET_NAME}${NC}"
    
    # Import Subnets
    for SUBNET_NAME in "${PROJECT_NAME}-compute-subnet-${ENVIRONMENT}" "${PROJECT_NAME}-data-subnet-${ENVIRONMENT}" "${PROJECT_NAME}-private-endpoint-subnet-${ENVIRONMENT}"; do
        SUBNET_ID=$(az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_NAME" --name "$SUBNET_NAME" --query id -o tsv 2>/dev/null || echo "")
        if [ -n "$SUBNET_ID" ]; then
            # Map subnet names to Terraform addresses
            case "$SUBNET_NAME" in
                *compute*)
                    TERRAFORM_ADDRESS="module.network.azurerm_subnet.compute"
                    ;;
                *data*)
                    TERRAFORM_ADDRESS="module.network.azurerm_subnet.data"
                    ;;
                *private-endpoint*)
                    TERRAFORM_ADDRESS="module.network.azurerm_subnet.private_endpoint"
                    ;;
                *)
                    TERRAFORM_ADDRESS="module.network.azurerm_subnet.${SUBNET_NAME}"
                    ;;
            esac
            add_import "azurerm_subnet" "$SUBNET_NAME" "$SUBNET_ID" "$TERRAFORM_ADDRESS"
            echo -e "${GREEN}  ✓ Found Subnet: ${SUBNET_NAME}${NC}"
        fi
    done
fi

# Import PostgreSQL Database
echo -e "${YELLOW}Checking PostgreSQL Database...${NC}"
POSTGRES_NAME="${PROJECT_NAME}-postgres-${ENVIRONMENT}"
POSTGRES_ID=$(az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_NAME" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$POSTGRES_ID" ]; then
    add_import "azurerm_postgresql_flexible_server" "$POSTGRES_NAME" "$POSTGRES_ID" "module.database.azurerm_postgresql_flexible_server.main"
    echo -e "${GREEN}✓ Found PostgreSQL: ${POSTGRES_NAME}${NC}"
    
    # Import PostgreSQL Database
    DB_NAME="lexiqai"
    DB_ID="${POSTGRES_ID}/databases/${DB_NAME}"
    add_import "azurerm_postgresql_flexible_server_database" "$DB_NAME" "$DB_ID" "module.database.azurerm_postgresql_flexible_server_database.main"
    echo -e "${GREEN}  ✓ Found Database: ${DB_NAME}${NC}"
fi

# Import Storage Account
echo -e "${YELLOW}Checking Storage Account...${NC}"
STORAGE_NAME=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, '${PROJECT_NAME}') && contains(name, '${ENVIRONMENT}')].name" -o tsv | head -1 || echo "")
if [ -n "$STORAGE_NAME" ]; then
    STORAGE_ID=$(az storage account show --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
    if [ -n "$STORAGE_ID" ]; then
        add_import "azurerm_storage_account" "$STORAGE_NAME" "$STORAGE_ID" "module.storage.azurerm_storage_account.main"
        echo -e "${GREEN}✓ Found Storage Account: ${STORAGE_NAME}${NC}"
    fi
fi

# Import Key Vault
echo -e "${YELLOW}Checking Key Vault...${NC}"
KV_NAME="${PROJECT_NAME}-kv-${ENVIRONMENT}"
KV_ID=$(az keyvault show --name "$KV_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$KV_ID" ]; then
    add_import "azurerm_key_vault" "$KV_NAME" "$KV_ID" "azurerm_key_vault.main[0]"
    echo -e "${GREEN}✓ Found Key Vault: ${KV_NAME}${NC}"
fi

# Import Container Registry
echo -e "${YELLOW}Checking Container Registry...${NC}"
ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, '${PROJECT_NAME}') && contains(name, '${ENVIRONMENT}')].name" -o tsv | head -1 || echo "")
if [ -n "$ACR_NAME" ]; then
    ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
    if [ -n "$ACR_ID" ]; then
        add_import "azurerm_container_registry" "$ACR_NAME" "$ACR_ID" "azurerm_container_registry.main"
        echo -e "${GREEN}✓ Found Container Registry: ${ACR_NAME}${NC}"
    fi
fi

# Import Log Analytics Workspace
echo -e "${YELLOW}Checking Log Analytics Workspace...${NC}"
LAW_NAME="${PROJECT_NAME}-logs-${ENVIRONMENT}"
LAW_ID=$(az monitor log-analytics workspace show --resource-group "$RESOURCE_GROUP" --workspace-name "$LAW_NAME" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$LAW_ID" ]; then
    add_import "azurerm_log_analytics_workspace" "$LAW_NAME" "$LAW_ID" "azurerm_log_analytics_workspace.main"
    echo -e "${GREEN}✓ Found Log Analytics Workspace: ${LAW_NAME}${NC}"
fi

# Import Application Insights
echo -e "${YELLOW}Checking Application Insights...${NC}"
AI_NAME="${PROJECT_NAME}-appinsights-${ENVIRONMENT}"
AI_ID=$(az monitor app-insights component show --app "$AI_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$AI_ID" ]; then
    add_import "azurerm_application_insights" "$AI_NAME" "$AI_ID" "azurerm_application_insights.main"
    echo -e "${GREEN}✓ Found Application Insights: ${AI_NAME}${NC}"
fi

# Import Static Web App
echo -e "${YELLOW}Checking Static Web App...${NC}"
SWA_NAME="${PROJECT_NAME}-web-${ENVIRONMENT}"
SWA_ID=$(az staticwebapp show --name "$SWA_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$SWA_ID" ]; then
    add_import "azurerm_static_web_app" "$SWA_NAME" "$SWA_ID" "azurerm_static_web_app.frontend"
    echo -e "${GREEN}✓ Found Static Web App: ${SWA_NAME}${NC}"
fi

# Import Managed Identity
echo -e "${YELLOW}Checking Managed Identity...${NC}"
MI_NAME="${PROJECT_NAME}-identity-${ENVIRONMENT}"
MI_ID=$(az identity show --name "$MI_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$MI_ID" ]; then
    add_import "azurerm_user_assigned_identity" "$MI_NAME" "$MI_ID" "module.identity.azurerm_user_assigned_identity.main"
    echo -e "${GREEN}✓ Found Managed Identity: ${MI_NAME}${NC}"
fi

# Import Container Apps Environment
echo -e "${YELLOW}Checking Container Apps Environment...${NC}"
CAE_NAME="${PROJECT_NAME}-cae-${ENVIRONMENT}"
CAE_ID=$(az containerapp env show --name "$CAE_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv 2>/dev/null || echo "")
if [ -n "$CAE_ID" ]; then
    add_import "azurerm_container_app_environment" "$CAE_NAME" "$CAE_ID" "module.container_apps.azurerm_container_app_environment.main"
    echo -e "${GREEN}✓ Found Container Apps Environment: ${CAE_NAME}${NC}"
    
    # Import Container Apps
    CONTAINER_APPS=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, '${PROJECT_NAME}') && contains(name, '${ENVIRONMENT}')].{name:name, id:id}" -o json 2>/dev/null || echo "[]")
    if [ -n "$CONTAINER_APPS" ] && [ "$CONTAINER_APPS" != "[]" ]; then
        echo "$CONTAINER_APPS" | jq -r '.[] | "\(.name)|\(.id)"' | while IFS='|' read -r APP_NAME APP_ID; do
            # Map container app names to Terraform addresses
            case "$APP_NAME" in
                *api-core*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.api_core"
                    ;;
                *cognitive-orch*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.cognitive_orch"
                    ;;
                *voice-gateway*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.voice_gateway"
                    ;;
                *document-ingestion*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.document_ingestion"
                    ;;
                *integration-worker*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.integration_worker"
                    ;;
                *integration-worker-beat*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.integration_worker_beat"
                    ;;
                *integration-worker-webhooks*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.integration_worker_webhooks"
                    ;;
                *redis*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.redis"
                    ;;
                *qdrant*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.qdrant"
                    ;;
                *rabbitmq*)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.rabbitmq"
                    ;;
                *)
                    TERRAFORM_ADDRESS="module.container_apps.azurerm_container_app.${APP_NAME}"
                    ;;
            esac
            add_import "azurerm_container_app" "$APP_NAME" "$APP_ID" "$TERRAFORM_ADDRESS"
            echo -e "${GREEN}  ✓ Found Container App: ${APP_NAME}${NC}"
        done
    fi
fi

# Make the import script executable
chmod +x "$IMPORT_FILE"

echo ""
echo -e "${GREEN}✓ Generated ${IMPORT_COUNT} import commands in ${IMPORT_FILE}${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review the generated import commands:"
echo "   cat ${IMPORT_FILE}"
echo ""
echo "2. Run the import script:"
echo "   bash ${IMPORT_FILE}"
echo ""
echo "3. Verify with terraform plan:"
echo "   terraform plan -var-file=${VAR_FILE}"
