#!/bin/bash
# Script to build and push infrastructure service images (Redis, RabbitMQ, Qdrant) to shared ACR
# Usage: ./build-and-push-infrastructure-images.sh <environment> [shared-acr-name]
# Example: ./build-and-push-infrastructure-images.sh dev lexiqaiacrshared

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${GREEN}=== Build and Push Infrastructure Images ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Shared ACR: $SHARED_ACR_NAME"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
  echo -e "${RED}Error: Azure CLI is not installed${NC}"
  exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo -e "${RED}Error: Docker is not installed${NC}"
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

SHARED_ACR_LOGIN="${SHARED_ACR_NAME}.azurecr.io"

# Login to ACR
echo -e "${YELLOW}Logging in to ACR...${NC}"
az acr login --name "$SHARED_ACR_NAME"
echo -e "${GREEN}✓ Logged in to ACR${NC}"

# Services to build
declare -A SERVICES=(
  ["redis"]="docker/redis/Dockerfile"
  ["rabbitmq"]="docker/rabbitmq/Dockerfile"
  ["qdrant"]="docker/qdrant/Dockerfile"
)

BUILT_COUNT=0
FAILED_COUNT=0

cd "$PROJECT_ROOT"

for SERVICE in "${!SERVICES[@]}"; do
  DOCKERFILE="${SERVICES[$SERVICE]}"
  DOCKERFILE_PATH="$PROJECT_ROOT/$DOCKERFILE"
  
  # Check if Dockerfile exists
  if [ ! -f "$DOCKERFILE_PATH" ]; then
    echo -e "${YELLOW}⚠ Dockerfile not found: $DOCKERFILE_PATH${NC}"
    echo "  Skipping $SERVICE (you can create the Dockerfile or use import script instead)"
    continue
  fi
  
  # Determine build context (directory containing Dockerfile)
  DOCKERFILE_DIR=$(dirname "$DOCKERFILE_PATH")
  
  IMAGE_TAG="${ENVIRONMENT}-latest"
  IMAGE_NAME="${SHARED_ACR_LOGIN}/${PROJECT_NAME}/${SERVICE}:${IMAGE_TAG}"
  
  echo -e "${YELLOW}Building $SERVICE...${NC}"
  echo "  Dockerfile: $DOCKERFILE"
  echo "  Context: $DOCKERFILE_DIR"
  echo "  Image: $IMAGE_NAME"
  
  # Build image
  if docker build \
    -f "$DOCKERFILE_PATH" \
    -t "$IMAGE_NAME" \
    "$DOCKERFILE_DIR" &> /dev/null; then
    echo -e "${GREEN}✓ Built $SERVICE${NC}"
    
    # Push image
    echo -e "${YELLOW}  Pushing to ACR...${NC}"
    if docker push "$IMAGE_NAME" &> /dev/null; then
      echo -e "${GREEN}✓ Pushed $SERVICE${NC}"
      BUILT_COUNT=$((BUILT_COUNT + 1))
    else
      echo -e "${RED}✗ Failed to push $SERVICE${NC}"
      FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
  else
    echo -e "${RED}✗ Failed to build $SERVICE${NC}"
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
  echo ""
done

# Summary
echo -e "${GREEN}=== Build Summary ===${NC}"
echo "Successfully built and pushed: $BUILT_COUNT images"
if [ $FAILED_COUNT -gt 0 ]; then
  echo -e "${RED}Failed: $FAILED_COUNT images${NC}"
fi
echo ""

if [ $BUILT_COUNT -gt 0 ]; then
  echo -e "${GREEN}Images built and pushed!${NC}"
  echo ""
  echo "Next steps:"
  echo "1. Apply Terraform to update Container Apps:"
  echo "   cd infra/terraform"
  echo "   terraform apply -var-file=dev.tfvars"
  echo "2. Verify Container Apps are using ACR images:"
  echo "   make verify-shared-resources ENV=${ENVIRONMENT}"
else
  echo -e "${YELLOW}No images were built${NC}"
  echo ""
  echo "If Dockerfiles don't exist, you can:"
  echo "1. Create Dockerfiles in docker/redis/, docker/rabbitmq/, docker/qdrant/"
  echo "2. Or use the import script to import public images:"
  echo "   make import-public-images-acr ENV=${ENVIRONMENT}"
fi
