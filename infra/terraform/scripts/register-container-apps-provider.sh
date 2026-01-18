#!/bin/bash
# Script to register the Microsoft.App provider for Container Apps
# This is required before creating Container Apps resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Registering Microsoft.App provider for Container Apps...${NC}"
echo ""

# Check if logged into Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}Error: Not logged into Azure CLI${NC}"
    echo "Please run: az login"
    exit 1
fi

# Get current subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

echo -e "${YELLOW}Current subscription:${NC}"
echo "  ID: ${SUBSCRIPTION_ID}"
echo "  Name: ${SUBSCRIPTION_NAME}"
echo ""

# Register Microsoft.App provider
echo -e "${YELLOW}Registering Microsoft.App provider...${NC}"
az provider register --namespace Microsoft.App --wait

# Check registration status
echo ""
echo -e "${YELLOW}Checking registration status...${NC}"
STATUS=$(az provider show --namespace Microsoft.App --query "registrationState" -o tsv)

if [ "$STATUS" = "Registered" ]; then
    echo -e "${GREEN}✓ Microsoft.App provider is registered${NC}"
else
    echo -e "${YELLOW}⚠ Registration status: ${STATUS}${NC}"
    echo "  This may take a few minutes. You can check status with:"
    echo "  az provider show --namespace Microsoft.App --query registrationState"
fi

echo ""
echo -e "${GREEN}Provider registration complete!${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} If registration is still in progress, wait a few minutes and try running Terraform again."
