#!/bin/bash
# Script to verify that all Container Apps are using shared resources
# Usage: ./verify-shared-resources.sh <environment> [shared-acr-name]
# Example: ./verify-shared-resources.sh dev lexiqaiacrshared

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
  echo -e "${RED}Error: Environment is required${NC}"
  echo "Usage: $0 <environment> [shared-acr-name]"
  echo "Example: $0 dev lexiqaiacrshared"
  exit 1
fi

ENVIRONMENT=$1
SHARED_ACR_NAME=${2:-"lexiqaiacrshared"}
PROJECT_NAME="lexiqai"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

echo -e "${GREEN}=== Shared Resources Verification Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Shared ACR: $SHARED_ACR_NAME"
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

# Verify resource group exists
echo -e "${YELLOW}Checking resource group...${NC}"
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
  echo -e "${RED}Error: Resource group '$RESOURCE_GROUP' does not exist${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Resource group found${NC}"

# Verify shared ACR exists
echo -e "${YELLOW}Checking shared ACR...${NC}"
if ! az acr show --name "$SHARED_ACR_NAME" &> /dev/null; then
  echo -e "${RED}Error: Shared ACR '$SHARED_ACR_NAME' does not exist${NC}"
  echo -e "${YELLOW}Hint: Make sure shared resources are created (Phase 1)${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Shared ACR found${NC}"

# Get shared ACR login server
SHARED_ACR_LOGIN=$(az acr show --name "$SHARED_ACR_NAME" --query "loginServer" -o tsv)
echo "Shared ACR login server: $SHARED_ACR_LOGIN"
echo ""

# Check Container Apps
echo -e "${YELLOW}Checking Container Apps...${NC}"
CONTAINER_APPS=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[].{name:name, image:properties.template.containers[0].image}" -o json)

if [ -z "$CONTAINER_APPS" ] || [ "$CONTAINER_APPS" == "[]" ]; then
  echo -e "${YELLOW}No Container Apps found in resource group${NC}"
  exit 0
fi

# Check each Container App
USING_SHARED=0
USING_OLD=0
USING_PUBLIC=0
ISSUES=()

# Public images that are acceptable (infrastructure services)
PUBLIC_IMAGES=("redis:" "rabbitmq:" "qdrant/")

while IFS= read -r app; do
  APP_NAME=$(echo "$app" | jq -r '.name')
  IMAGE=$(echo "$app" | jq -r '.image')
  
  # Check if it's a public image (acceptable for infrastructure services)
  IS_PUBLIC=false
  for public_img in "${PUBLIC_IMAGES[@]}"; do
    if [[ "$IMAGE" == *"$public_img"* ]]; then
      IS_PUBLIC=true
      break
    fi
  done
  
  if [[ "$IMAGE" == *"$SHARED_ACR_LOGIN"* ]]; then
    echo -e "${GREEN}✓ $APP_NAME is using shared ACR${NC}"
    echo "  Image: $IMAGE"
    USING_SHARED=$((USING_SHARED + 1))
  elif [ "$IS_PUBLIC" == "true" ]; then
    echo -e "${YELLOW}○ $APP_NAME is using public image (acceptable)${NC}"
    echo "  Image: $IMAGE"
    USING_PUBLIC=$((USING_PUBLIC + 1))
  else
    echo -e "${RED}✗ $APP_NAME is NOT using shared ACR${NC}"
    echo "  Image: $IMAGE"
    USING_OLD=$((USING_OLD + 1))
    ISSUES+=("$APP_NAME")
  fi
done < <(echo "$CONTAINER_APPS" | jq -c '.[]')

echo ""

# Summary
echo -e "${GREEN}=== Verification Summary ===${NC}"
echo "Container Apps using shared ACR: $USING_SHARED"
echo "Container Apps using public images: $USING_PUBLIC (acceptable for infrastructure services)"
if [ $USING_OLD -gt 0 ]; then
  echo -e "${RED}Container Apps using old ACR: $USING_OLD${NC}"
  echo ""
  echo -e "${RED}⚠️  WARNING: Some Container Apps are still using old ACR!${NC}"
  echo "Container Apps that need attention:"
  for app in "${ISSUES[@]}"; do
    echo "  - $app"
  done
  echo ""
  echo "Before proceeding with cleanup:"
  echo "1. Update these Container Apps to use shared ACR"
  echo "2. Verify all applications are working correctly"
  echo "3. Re-run this verification script"
  exit 1
else
  echo -e "${GREEN}✓ All application Container Apps are using shared ACR or public images${NC}"
  echo ""
  echo -e "${GREEN}Safe to proceed with cleanup!${NC}"
  exit 0
fi
