#!/bin/bash
# Script to check Azure subscription status and service accessibility
# Useful for troubleshooting "ReadOnlyDisabledSubscription" errors

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Azure Subscription Status Check${NC}"
echo "=================================="
echo ""

# Source .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Get project name and environment from tfvars
PROJECT_NAME=$(awk -F'=' '/^[[:space:]]*project_name[[:space:]]*=/ {gsub(/[" ]/, "", $2); print $2}' dev.tfvars 2>/dev/null || echo "lexiqai")
ENVIRONMENT=$(awk -F'=' '/^[[:space:]]*environment[[:space:]]*=/ {gsub(/[" ]/, "", $2); print $2}' dev.tfvars 2>/dev/null || echo "dev")
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

echo -e "${YELLOW}Checking subscription status...${NC}"
echo ""

# Check subscription status
SUBSCRIPTION_INFO=$(az account show 2>/dev/null || echo "")
if [ -z "$SUBSCRIPTION_INFO" ]; then
    echo -e "${RED}✗ Not logged into Azure CLI${NC}"
    echo "  Run: az login"
    exit 1
fi

SUBSCRIPTION_ID=$(echo "$SUBSCRIPTION_INFO" | grep -o '"id": "[^"]*' | cut -d'"' -f4)
SUBSCRIPTION_NAME=$(echo "$SUBSCRIPTION_INFO" | grep -o '"name": "[^"]*' | cut -d'"' -f4)
SUBSCRIPTION_STATE=$(echo "$SUBSCRIPTION_INFO" | grep -o '"state": "[^"]*' | cut -d'"' -f4)

echo -e "${BLUE}Subscription Details:${NC}"
echo "  ID: ${SUBSCRIPTION_ID}"
echo "  Name: ${SUBSCRIPTION_NAME}"
echo "  State: ${SUBSCRIPTION_STATE}"
echo ""

if [ "$SUBSCRIPTION_STATE" != "Enabled" ]; then
    echo -e "${RED}✗ Subscription is not enabled${NC}"
    echo "  Please re-enable your subscription in Azure Portal"
    exit 1
fi

echo -e "${GREEN}✓ Subscription is enabled${NC}"
echo ""

# Check resource group access
echo -e "${YELLOW}Checking resource group access...${NC}"
if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    echo -e "${GREEN}✓ Resource group '${RESOURCE_GROUP}' is accessible${NC}"
else
    echo -e "${RED}✗ Cannot access resource group '${RESOURCE_GROUP}'${NC}"
    echo "  This might indicate a propagation delay or permission issue"
fi
echo ""

# Check Key Vault access
KEY_VAULT_NAME="${PROJECT_NAME}-kv-${ENVIRONMENT}"
echo -e "${YELLOW}Checking Key Vault access...${NC}"
if az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo -e "${GREEN}✓ Key Vault '${KEY_VAULT_NAME}' is accessible${NC}"
else
    ERROR=$(az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP" 2>&1 || true)
    if echo "$ERROR" | grep -q "ReadOnlyDisabledSubscription"; then
        echo -e "${RED}✗ Key Vault access blocked: Subscription still in read-only mode${NC}"
        echo -e "${YELLOW}  This is a propagation delay - wait 15-30 minutes and try again${NC}"
    else
        echo -e "${YELLOW}⚠ Key Vault '${KEY_VAULT_NAME}' not found or not accessible${NC}"
        echo "  Error: ${ERROR}"
    fi
fi
echo ""

# Check Storage Account access
STORAGE_NAME="${PROJECT_NAME}storage${ENVIRONMENT}"
echo -e "${YELLOW}Checking Storage Account access...${NC}"
if az storage account show --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo -e "${GREEN}✓ Storage Account '${STORAGE_NAME}' is accessible${NC}"
else
    ERROR=$(az storage account show --name "$STORAGE_NAME" --resource-group "$RESOURCE_GROUP" 2>&1 || true)
    if echo "$ERROR" | grep -q "ReadOnlyDisabledSubscription"; then
        echo -e "${RED}✗ Storage Account access blocked: Subscription still in read-only mode${NC}"
        echo -e "${YELLOW}  This is a propagation delay - wait 15-30 minutes and try again${NC}"
    else
        echo -e "${YELLOW}⚠ Storage Account '${STORAGE_NAME}' not found or not accessible${NC}"
    fi
fi
echo ""

# Summary
echo -e "${BLUE}Summary:${NC}"
echo "  If you see 'ReadOnlyDisabledSubscription' errors, Azure services are still"
echo "  propagating the subscription state change. This typically takes 15-30 minutes."
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Wait 15-30 minutes"
echo "  2. Run this script again: bash scripts/check-subscription-status.sh"
echo "  3. Once all services are accessible, run: make terraform-refresh"
echo ""
