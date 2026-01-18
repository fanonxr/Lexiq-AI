#!/bin/bash
# Script to check Container App status and diagnose 412 Precondition Failed errors

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
APP_NAME="${PROJECT_NAME}-iw-beat-${ENVIRONMENT}"

echo -e "${YELLOW}Checking Container App status...${NC}"
echo -e "${YELLOW}Resource Group: ${RESOURCE_GROUP}${NC}"
echo -e "${YELLOW}Container App: ${APP_NAME}${NC}"
echo ""

# Check if logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged in to Azure. Run 'az login' first.${NC}"
    exit 1
fi

# Check if Container App exists
echo -e "${YELLOW}Checking if Container App exists...${NC}"
APP_EXISTS=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "name" -o tsv 2>/dev/null)

if [ -z "$APP_EXISTS" ]; then
    echo -e "${RED}✗ Container App '${APP_NAME}' does not exist in Azure${NC}"
    echo ""
    echo -e "${YELLOW}Solution:${NC}"
    echo -e "  Remove it from Terraform state:"
    echo -e "  ${GREEN}cd infra/terraform${NC}"
    echo -e "  ${GREEN}terraform state rm module.container_apps.azurerm_container_app.integration_worker_beat${NC}"
    echo -e "  ${GREEN}terraform apply${NC}"
    exit 0
fi

echo -e "${GREEN}✓ Container App exists${NC}"
echo ""

# Get Container App status
echo -e "${YELLOW}Container App Status:${NC}"
PROVISIONING_STATE=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.provisioningState" -o tsv 2>/dev/null)
LATEST_REVISION=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.latestRevisionName" -o tsv 2>/dev/null)
LATEST_REVISION_STATUS=$(az containerapp revision show --name "$LATEST_REVISION" --app "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.runningState" -o tsv 2>/dev/null)

echo -e "  Provisioning State: ${PROVISIONING_STATE}"
echo -e "  Latest Revision: ${LATEST_REVISION}"
echo -e "  Revision Status: ${LATEST_REVISION_STATUS}"
echo ""

# Check for failed state
if [ "$PROVISIONING_STATE" == "Failed" ]; then
    echo -e "${RED}✗ Container App is in 'Failed' state${NC}"
    echo ""
    echo -e "${YELLOW}Solution:${NC}"
    echo -e "  1. Delete the failed Container App:"
    echo -e "     ${GREEN}az containerapp delete --name ${APP_NAME} --resource-group ${RESOURCE_GROUP} --yes${NC}"
    echo -e ""
    echo -e "  2. Remove from Terraform state:"
    echo -e "     ${GREEN}cd infra/terraform${NC}"
    echo -e "     ${GREEN}terraform state rm module.container_apps.azurerm_container_app.integration_worker_beat${NC}"
    echo -e ""
    echo -e "  3. Recreate with Terraform:"
    echo -e "     ${GREEN}terraform apply${NC}"
    exit 1
fi

# Check for transitional states
if [[ "$PROVISIONING_STATE" == "Updating" ]] || [[ "$PROVISIONING_STATE" == "Creating" ]]; then
    echo -e "${YELLOW}⚠ Container App is in transitional state: ${PROVISIONING_STATE}${NC}"
    echo -e "${YELLOW}Wait a few minutes and try again.${NC}"
    exit 0
fi

# Check revision status
if [ "$LATEST_REVISION_STATUS" == "Failed" ]; then
    echo -e "${RED}✗ Latest revision is in 'Failed' state${NC}"
    echo ""
    echo -e "${YELLOW}Getting revision details...${NC}"
    az containerapp revision show --name "$LATEST_REVISION" --app "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties" -o json | jq -r '.healthState, .trafficWeight, .replicas'
    echo ""
    echo -e "${YELLOW}Solution:${NC}"
    echo -e "  The revision failed to start. Check the logs:"
    echo -e "  ${GREEN}az containerapp logs show --name ${APP_NAME} --resource-group ${RESOURCE_GROUP} --follow${NC}"
    exit 1
fi

# If we get here, the Container App seems healthy
if [ "$PROVISIONING_STATE" == "Succeeded" ] && [ "$LATEST_REVISION_STATUS" == "Running" ]; then
    echo -e "${GREEN}✓ Container App is healthy${NC}"
    echo ""
    echo -e "${YELLOW}The 412 error might be transient. Try:${NC}"
    echo -e "  1. Wait a few minutes and run terraform refresh again"
    echo -e "  2. Or run terraform apply to sync the state"
else
    echo -e "${YELLOW}⚠ Container App state: ${PROVISIONING_STATE} / ${LATEST_REVISION_STATUS}${NC}"
    echo -e "${YELLOW}This might be causing the 412 error.${NC}"
fi
