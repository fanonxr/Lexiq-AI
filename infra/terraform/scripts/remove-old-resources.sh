#!/bin/bash
# Script to remove old resources from Terraform state
# These resources were removed from the configuration but may still exist in state
# Run this script before terraform destroy if you see errors about missing resources
# This script works even when Azure subscription is disabled (read-only mode)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Removing old resources from Terraform state...${NC}"
echo -e "${YELLOW}Note: This works even if your Azure subscription is disabled${NC}"
echo ""

# Change to terraform directory
cd "$(dirname "$0")/.."

# Source .env if it exists
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
fi

# Use -refresh=false to avoid trying to read from Azure (important when subscription is disabled)
REFRESH_FLAG="-refresh=false"

# List of resources to remove from state (if they exist)
# These are patterns that might match resources in state
RESOURCE_PATTERNS=(
    "module.openai"
    "module.cache"
    "azurerm_key_vault_secret.openai_api_key"
    "azurerm_key_vault_secret.openai_endpoint"
    "azurerm_cognitive_account"
    "azurerm_redis_cache"
)

REMOVED_COUNT=0
NOT_FOUND_COUNT=0

# First, list all resources in state (without refreshing)
echo -e "${YELLOW}Listing resources in state...${NC}"
STATE_LIST=$(terraform state list ${REFRESH_FLAG} 2>/dev/null || echo "")

if [ -z "$STATE_LIST" ]; then
    echo -e "${RED}Error: Could not list Terraform state. Make sure you're in the correct directory and state file exists.${NC}"
    exit 1
fi

# Check for each pattern
for pattern in "${RESOURCE_PATTERNS[@]}"; do
    # Find matching resources in state
    MATCHING_RESOURCES=$(echo "$STATE_LIST" | grep -E "^${pattern}(/|$)" || true)
    
    if [ -n "$MATCHING_RESOURCES" ]; then
        while IFS= read -r resource; do
            if [ -n "$resource" ]; then
                echo -e "${YELLOW}Found ${resource}, removing from state...${NC}"
                # Use -var-file and -refresh=false to avoid Azure API calls
                if terraform state rm ${REFRESH_FLAG} -var-file=dev.tfvars "${resource}" 2>/dev/null; then
                    echo -e "${GREEN}  ✓ Removed ${resource}${NC}"
                    ((REMOVED_COUNT++))
                else
                    # Try without var-file if that fails
                    if terraform state rm ${REFRESH_FLAG} "${resource}" 2>/dev/null; then
                        echo -e "${GREEN}  ✓ Removed ${resource}${NC}"
                        ((REMOVED_COUNT++))
                    else
                        echo -e "${RED}  ✗ Failed to remove ${resource}${NC}"
                    fi
                fi
            fi
        done <<< "$MATCHING_RESOURCES"
    else
        echo -e "${YELLOW}  No resources found matching pattern: ${pattern}${NC}"
        ((NOT_FOUND_COUNT++))
    fi
done

echo ""
echo -e "${GREEN}✓ Removed ${REMOVED_COUNT} resource(s) from state${NC}"
echo -e "${YELLOW}  ${NOT_FOUND_COUNT} pattern(s) had no matches${NC}"
echo ""
echo -e "${YELLOW}If you still see errors, you can manually check and remove resources:${NC}"
echo "  terraform state list -refresh=false | grep -E 'openai|cache'"
echo "  terraform state rm -refresh=false <resource-address>"
echo ""
echo -e "${GREEN}You can now run 'terraform destroy -refresh=false' or 'make terraform-destroy-no-refresh'${NC}"
