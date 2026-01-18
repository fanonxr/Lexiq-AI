#!/bin/bash
# Script to update Container Apps to use shared ACR images
# Usage: ./update-container-apps-to-shared-acr.sh <environment> [shared-acr-name]
# Example: ./update-container-apps-to-shared-acr.sh dev lexiqaiacrshared

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

echo -e "${GREEN}=== Update Container Apps to Shared ACR ===${NC}"
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

# Verify shared ACR exists
echo -e "${YELLOW}Checking shared ACR...${NC}"
if ! az acr show --name "$SHARED_ACR_NAME" &> /dev/null; then
  echo -e "${RED}Error: Shared ACR '$SHARED_ACR_NAME' does not exist${NC}"
  echo -e "${YELLOW}Hint: Make sure shared resources are created (Phase 1)${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Shared ACR found${NC}"

SHARED_ACR_LOGIN=$(az acr show --name "$SHARED_ACR_NAME" --query "loginServer" -o tsv)
echo "Shared ACR login server: $SHARED_ACR_LOGIN"
echo ""

# Services that need to be updated (excluding public images)
SERVICES=("api-core" "cognitive-orch" "voice-gateway" "document-ingestion" "integration-worker")

# Get all Container Apps
echo -e "${YELLOW}Getting Container Apps...${NC}"
CONTAINER_APPS=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[].{name:name, image:properties.template.containers[0].image}" -o json)

if [ -z "$CONTAINER_APPS" ] || [ "$CONTAINER_APPS" == "[]" ]; then
  echo -e "${YELLOW}No Container Apps found${NC}"
  exit 0
fi

UPDATED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0

# Update each service
for SERVICE in "${SERVICES[@]}"; do
  APP_NAME="${PROJECT_NAME}-${SERVICE}-${ENVIRONMENT}"
  
  # Check if Container App exists
  APP_DATA=$(echo "$CONTAINER_APPS" | jq -r ".[] | select(.name == \"$APP_NAME\")")
  
  if [ -z "$APP_DATA" ] || [ "$APP_DATA" == "null" ]; then
    echo -e "${YELLOW}⚠ Container App '$APP_NAME' not found, skipping...${NC}"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    continue
  fi
  
  CURRENT_IMAGE=$(echo "$APP_DATA" | jq -r '.image')
  
  # Check if already using shared ACR
  if [[ "$CURRENT_IMAGE" == *"$SHARED_ACR_LOGIN"* ]]; then
    echo -e "${GREEN}✓ $APP_NAME already using shared ACR${NC}"
    echo "  Image: $CURRENT_IMAGE"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    continue
  fi
  
  # Extract tag from current image
  if [[ "$CURRENT_IMAGE" == *":"* ]]; then
    TAG=$(echo "$CURRENT_IMAGE" | cut -d':' -f2)
  else
    TAG="latest"
  fi
  
  # Create new image reference with environment prefix
  # If tag doesn't already have environment prefix, add it
  if [[ "$TAG" != "${ENVIRONMENT}-"* ]]; then
    NEW_TAG="${ENVIRONMENT}-${TAG}"
  else
    NEW_TAG="$TAG"
  fi
  
  NEW_IMAGE="${SHARED_ACR_LOGIN}/${PROJECT_NAME}/${SERVICE}:${NEW_TAG}"
  
  # If the environment-prefixed tag doesn't exist, try without prefix or use latest
  echo -e "${YELLOW}Checking if image exists in shared ACR: ${PROJECT_NAME}/${SERVICE}:${NEW_TAG}${NC}"
  if ! az acr repository show-tags --name "$SHARED_ACR_NAME" --repository "${PROJECT_NAME}/${SERVICE}" --query "[?contains(@, '${NEW_TAG}')]" -o tsv 2>/dev/null | grep -q .; then
    # Try with just the tag (without environment prefix)
    if ! az acr repository show-tags --name "$SHARED_ACR_NAME" --repository "${PROJECT_NAME}/${SERVICE}" --query "[?contains(@, '${TAG}')]" -o tsv 2>/dev/null | grep -q .; then
      # Try latest
      if az acr repository show-tags --name "$SHARED_ACR_NAME" --repository "${PROJECT_NAME}/${SERVICE}" --query "[?contains(@, 'latest')]" -o tsv 2>/dev/null | grep -q .; then
        NEW_TAG="${ENVIRONMENT}-latest"
        NEW_IMAGE="${SHARED_ACR_LOGIN}/${PROJECT_NAME}/${SERVICE}:${NEW_TAG}"
        echo -e "${YELLOW}  Using ${NEW_TAG} instead${NC}"
      else
        echo -e "${RED}✗ Image not found in shared ACR, skipping...${NC}"
        echo -e "${YELLOW}  Hint: Run 'make migrate-acr-images ENV=${ENVIRONMENT}' first${NC}"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        continue
      fi
    else
      NEW_TAG="$TAG"
      NEW_IMAGE="${SHARED_ACR_LOGIN}/${PROJECT_NAME}/${SERVICE}:${NEW_TAG}"
    fi
  fi
  
  echo -e "${YELLOW}Updating $APP_NAME...${NC}"
  echo "  From: $CURRENT_IMAGE"
  echo "  To:   $NEW_IMAGE"
  
  # Update Container App
  if az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$NEW_IMAGE" \
    --query "properties.latestRevisionName" -o tsv &> /dev/null; then
    echo -e "${GREEN}✓ Updated $APP_NAME${NC}"
    UPDATED_COUNT=$((UPDATED_COUNT + 1))
  else
    echo -e "${RED}✗ Failed to update $APP_NAME${NC}"
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
  echo ""
done

# Summary
echo -e "${GREEN}=== Update Summary ===${NC}"
echo "Updated: $UPDATED_COUNT Container Apps"
echo "Skipped: $SKIPPED_COUNT Container Apps (already using shared ACR or not found)"
if [ $FAILED_COUNT -gt 0 ]; then
  echo -e "${RED}Failed: $FAILED_COUNT Container Apps${NC}"
fi
echo ""

if [ $UPDATED_COUNT -gt 0 ]; then
  echo -e "${GREEN}✓ Container Apps updated!${NC}"
  echo ""
  echo "Next steps:"
  echo "1. Wait for new revisions to be ready"
  echo "2. Verify applications are working correctly"
  echo "3. Run 'make verify-shared-resources ENV=${ENVIRONMENT}' to confirm"
else
  echo -e "${YELLOW}No Container Apps were updated${NC}"
  if [ $FAILED_COUNT -gt 0 ]; then
    echo "Some updates failed. Check the errors above."
  fi
fi
