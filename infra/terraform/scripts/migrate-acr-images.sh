#!/bin/bash
# Script to migrate container images from environment-specific ACR to shared ACR
# Usage: ./migrate-acr-images.sh <environment> [shared-acr-name]
# Example: ./migrate-acr-images.sh dev lexiqaiacrshared

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
ENV_ACR_NAME="${PROJECT_NAME}acr${ENVIRONMENT}"

# Services to migrate
SERVICES=("api-core" "cognitive-orch" "voice-gateway" "document-ingestion" "integration-worker")

echo -e "${GREEN}=== ACR Image Migration Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Source ACR: $ENV_ACR_NAME"
echo "Target ACR: $SHARED_ACR_NAME"
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

# Verify source ACR exists
echo -e "${YELLOW}Checking source ACR: $ENV_ACR_NAME${NC}"
if ! az acr show --name "$ENV_ACR_NAME" &> /dev/null; then
  echo -e "${RED}Error: Source ACR '$ENV_ACR_NAME' does not exist${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Source ACR found${NC}"

# Verify target ACR exists
echo -e "${YELLOW}Checking target ACR: $SHARED_ACR_NAME${NC}"
if ! az acr show --name "$SHARED_ACR_NAME" &> /dev/null; then
  echo -e "${RED}Error: Target ACR '$SHARED_ACR_NAME' does not exist${NC}"
  echo -e "${YELLOW}Hint: Make sure shared resources are created (Phase 1)${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Target ACR found${NC}"

# List repositories in source ACR
echo ""
echo -e "${YELLOW}Listing repositories in source ACR...${NC}"
REPOS=$(az acr repository list --name "$ENV_ACR_NAME" --output tsv)

if [ -z "$REPOS" ]; then
  echo -e "${YELLOW}No repositories found in source ACR${NC}"
  exit 0
fi

echo "Found repositories:"
echo "$REPOS"
echo ""

# Migrate each service
MIGRATED_COUNT=0
FAILED_COUNT=0

for SERVICE in "${SERVICES[@]}"; do
  REPO_PATH="${PROJECT_NAME}/${SERVICE}"
  
  # Check if repository exists in source ACR
  if ! echo "$REPOS" | grep -q "^${REPO_PATH}$"; then
    echo -e "${YELLOW}⚠ Repository '${REPO_PATH}' not found in source ACR, skipping...${NC}"
    continue
  fi
  
  echo -e "${YELLOW}Migrating ${REPO_PATH}...${NC}"
  
  # List tags in source repository
  TAGS=$(az acr repository show-tags --name "$ENV_ACR_NAME" --repository "$REPO_PATH" --output tsv --orderby time_desc)
  
  if [ -z "$TAGS" ]; then
    echo -e "${YELLOW}  ⚠ No tags found for ${REPO_PATH}, skipping...${NC}"
    continue
  fi
  
  # Migrate each tag
  for TAG in $TAGS; do
    SOURCE_IMAGE="${ENV_ACR_NAME}.azurecr.io/${REPO_PATH}:${TAG}"
    TARGET_TAG="${ENVIRONMENT}-${TAG}"  # Prefix with environment
    TARGET_IMAGE="${SHARED_ACR_NAME}.azurecr.io/${REPO_PATH}:${TARGET_TAG}"
    
    echo -e "  Migrating ${TAG} → ${TARGET_TAG}..."
    
    # Import image to shared ACR
    if az acr import \
      --name "$SHARED_ACR_NAME" \
      --source "$SOURCE_IMAGE" \
      --image "${REPO_PATH}:${TARGET_TAG}" \
      --force &> /dev/null; then
      echo -e "  ${GREEN}✓ Successfully migrated ${TAG}${NC}"
      MIGRATED_COUNT=$((MIGRATED_COUNT + 1))
    else
      echo -e "  ${RED}✗ Failed to migrate ${TAG}${NC}"
      FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
  done
  
  # Also migrate 'latest' tag if it exists and create environment-specific latest
  if echo "$TAGS" | grep -q "^latest$"; then
    SOURCE_IMAGE="${ENV_ACR_NAME}.azurecr.io/${REPO_PATH}:latest"
    TARGET_TAG="${ENVIRONMENT}-latest"
    TARGET_IMAGE="${SHARED_ACR_NAME}.azurecr.io/${REPO_PATH}:${TARGET_TAG}"
    
    echo -e "  Migrating latest → ${TARGET_TAG}..."
    
    if az acr import \
      --name "$SHARED_ACR_NAME" \
      --source "$SOURCE_IMAGE" \
      --image "${REPO_PATH}:${TARGET_TAG}" \
      --force &> /dev/null; then
      echo -e "  ${GREEN}✓ Successfully migrated latest${NC}"
      MIGRATED_COUNT=$((MIGRATED_COUNT + 1))
    else
      echo -e "  ${RED}✗ Failed to migrate latest${NC}"
      FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
  fi
  
  echo ""
done

# Summary
echo -e "${GREEN}=== Migration Summary ===${NC}"
echo "Successfully migrated: $MIGRATED_COUNT images"
if [ $FAILED_COUNT -gt 0 ]; then
  echo -e "${RED}Failed: $FAILED_COUNT images${NC}"
fi
echo ""

# Verify migrated images
echo -e "${YELLOW}Verifying migrated images in shared ACR...${NC}"
for SERVICE in "${SERVICES[@]}"; do
  REPO_PATH="${PROJECT_NAME}/${SERVICE}"
  ENV_TAGS=$(az acr repository show-tags --name "$SHARED_ACR_NAME" --repository "$REPO_PATH" --output tsv 2>/dev/null | grep "^${ENVIRONMENT}-" || true)
  
  if [ -n "$ENV_TAGS" ]; then
    echo -e "${GREEN}✓ ${REPO_PATH} has ${ENVIRONMENT} tags:${NC}"
    echo "$ENV_TAGS" | sed 's/^/  - /'
  fi
done

echo ""
echo -e "${GREEN}Migration complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update Container Apps to use shared ACR images"
echo "2. Test applications with migrated images"
echo "3. After verification, proceed with Phase 7 cleanup"
