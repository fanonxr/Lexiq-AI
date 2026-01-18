#!/bin/bash
# Script to import public Docker images into shared ACR
# This is optional - public images work fine, but importing provides:
# - Rate limit protection (Docker Hub rate limits)
# - Faster pulls (ACR is closer to Container Apps)
# - Consistency with other images
# Usage: ./import-public-images-to-acr.sh <environment> [shared-acr-name]
# Example: ./import-public-images-to-acr.sh dev lexiqaiacrshared

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

echo -e "${GREEN}=== Import Public Images to Shared ACR ===${NC}"
echo "Environment: $ENVIRONMENT"
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
  exit 1
fi
echo -e "${GREEN}✓ Shared ACR found${NC}"

# Public images to import
declare -A PUBLIC_IMAGES=(
  ["redis"]="redis:7-alpine"
  ["rabbitmq"]="rabbitmq:3-management-alpine"
  ["qdrant"]="qdrant/qdrant:latest"
)

IMPORTED_COUNT=0
FAILED_COUNT=0

for SERVICE in "${!PUBLIC_IMAGES[@]}"; do
  SOURCE_IMAGE="${PUBLIC_IMAGES[$SERVICE]}"
  TARGET_IMAGE="${PROJECT_NAME}/${SERVICE}:${ENVIRONMENT}-latest"
  
  echo -e "${YELLOW}Importing $SOURCE_IMAGE → $TARGET_IMAGE...${NC}"
  
  # Import image to shared ACR
  if az acr import \
    --name "$SHARED_ACR_NAME" \
    --source "docker.io/${SOURCE_IMAGE}" \
    --image "$TARGET_IMAGE" \
    --force &> /dev/null; then
    echo -e "${GREEN}✓ Successfully imported $SERVICE${NC}"
    IMPORTED_COUNT=$((IMPORTED_COUNT + 1))
  else
    echo -e "${RED}✗ Failed to import $SERVICE${NC}"
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
done

# Summary
echo ""
echo -e "${GREEN}=== Import Summary ===${NC}"
echo "Successfully imported: $IMPORTED_COUNT images"
if [ $FAILED_COUNT -gt 0 ]; then
  echo -e "${RED}Failed: $FAILED_COUNT images${NC}"
fi
echo ""

if [ $IMPORTED_COUNT -gt 0 ]; then
  echo -e "${GREEN}Images imported!${NC}"
  echo ""
  echo "Next steps:"
  echo "1. Update Terraform to use ACR images instead of public images"
  echo "2. Apply Terraform changes"
  echo "3. Verify Container Apps are using ACR images"
else
  echo -e "${YELLOW}No images were imported${NC}"
fi
