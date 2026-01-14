#!/bin/bash
# Script to remove old environment-specific DNS zone from Terraform state and optionally delete from Azure
# Usage: ./cleanup-old-dns-zone.sh <environment> [dns-zone-name] [--delete-from-azure]
# Example: ./cleanup-old-dns-zone.sh dev lexiqai.com
# Example: ./cleanup-old-dns-zone.sh dev lexiqai.com --delete-from-azure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
  echo -e "${RED}Error: Environment is required${NC}"
  echo "Usage: $0 <environment> [dns-zone-name] [--delete-from-azure]"
  echo "Example: $0 dev lexiqai.com"
  echo "Example: $0 dev lexiqai.com --delete-from-azure"
  exit 1
fi

ENVIRONMENT=$1
DNS_ZONE_NAME=${2:-""}
DELETE_FROM_AZURE=false
if [ "$3" == "--delete-from-azure" ]; then
  DELETE_FROM_AZURE=true
fi

PROJECT_NAME="lexiqai"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

echo -e "${GREEN}=== Old DNS Zone Cleanup Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "DNS Zone Name: ${DNS_ZONE_NAME:-'(not specified)'}"
echo "Delete from Azure: $DELETE_FROM_AZURE"
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

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
  echo -e "${RED}Error: Terraform is not installed${NC}"
  exit 1
fi

# If DNS zone name is not provided, try to find it
if [ -z "$DNS_ZONE_NAME" ]; then
  echo -e "${YELLOW}DNS zone name not provided, searching for DNS zones in resource group...${NC}"
  DNS_ZONES=$(az network dns zone list --resource-group "$RESOURCE_GROUP" --query "[].name" -o tsv)
  
  if [ -z "$DNS_ZONES" ]; then
    echo -e "${YELLOW}No DNS zones found in resource group '$RESOURCE_GROUP'${NC}"
    echo "If you're not using Azure DNS, you can skip this step."
    exit 0
  fi
  
  DNS_ZONE_COUNT=$(echo "$DNS_ZONES" | wc -l)
  if [ "$DNS_ZONE_COUNT" -eq 1 ]; then
    DNS_ZONE_NAME=$(echo "$DNS_ZONES" | head -n 1)
    echo -e "${GREEN}Found DNS zone: $DNS_ZONE_NAME${NC}"
  else
    echo -e "${YELLOW}Multiple DNS zones found:${NC}"
    echo "$DNS_ZONES"
    echo -e "${RED}Please specify DNS zone name${NC}"
    exit 1
  fi
fi

# Change to Terraform directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/.."
cd "$TERRAFORM_DIR"

# Verify DNS zone exists in Azure
echo -e "${YELLOW}Checking if DNS zone exists in Azure...${NC}"
if az network dns zone show --resource-group "$RESOURCE_GROUP" --name "$DNS_ZONE_NAME" &> /dev/null; then
  echo -e "${GREEN}✓ DNS zone found in Azure${NC}"
  
  # List DNS records
  RECORD_COUNT=$(az network dns record-set list --resource-group "$RESOURCE_GROUP" --zone-name "$DNS_ZONE_NAME" --query "length(@)" -o tsv 2>/dev/null || echo "0")
  echo "  DNS records in zone: $RECORD_COUNT"
  
  if [ "$RECORD_COUNT" -gt 0 ] && [ "$DELETE_FROM_AZURE" == "true" ]; then
    echo -e "${YELLOW}⚠ WARNING: DNS zone contains $RECORD_COUNT records${NC}"
    echo "Deleting the zone will delete all records!"
  fi
else
  echo -e "${YELLOW}⚠ DNS zone not found in Azure (may already be deleted)${NC}"
fi

# Check if DNS zone is in Terraform state
echo ""
echo -e "${YELLOW}Checking Terraform state...${NC}"
if terraform state list 2>/dev/null | grep -q "azurerm_dns_zone.main"; then
  echo -e "${GREEN}✓ DNS zone found in Terraform state${NC}"
  
  # Remove DNS CNAME records from state first (if they exist)
  echo -e "${YELLOW}Checking for DNS CNAME records in state...${NC}"
  terraform state list 2>/dev/null | grep "azurerm_dns_cname_record" | while read -r resource; do
    echo -e "${YELLOW}Removing $resource from state...${NC}"
    terraform state rm "$resource" 2>/dev/null || true
  done
  
  # Remove DNS zone from state
  echo -e "${YELLOW}Removing DNS zone from Terraform state...${NC}"
  if terraform state rm 'azurerm_dns_zone.main[0]' 2>/dev/null; then
    echo -e "${GREEN}✓ Removed from Terraform state${NC}"
  else
    echo -e "${RED}✗ Failed to remove from Terraform state${NC}"
    echo "You may need to run this manually:"
    echo "  cd $TERRAFORM_DIR"
    echo "  terraform state rm 'azurerm_dns_zone.main[0]'"
    exit 1
  fi
else
  echo -e "${YELLOW}⚠ DNS zone not found in Terraform state (may already be removed)${NC}"
fi

# Delete from Azure if requested
if [ "$DELETE_FROM_AZURE" == "true" ]; then
  echo ""
  echo -e "${YELLOW}Deleting DNS zone from Azure...${NC}"
  if az network dns zone show --resource-group "$RESOURCE_GROUP" --name "$DNS_ZONE_NAME" &> /dev/null; then
    read -p "Are you sure you want to delete DNS zone '$DNS_ZONE_NAME'? This will delete all DNS records! (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
      if az network dns zone delete --resource-group "$RESOURCE_GROUP" --name "$DNS_ZONE_NAME" --yes; then
        echo -e "${GREEN}✓ DNS zone deleted from Azure${NC}"
      else
        echo -e "${RED}✗ Failed to delete DNS zone from Azure${NC}"
        exit 1
      fi
    else
      echo -e "${YELLOW}Cancelled deletion${NC}"
    fi
  else
    echo -e "${YELLOW}⚠ DNS zone not found in Azure (may already be deleted)${NC}"
  fi
else
  echo ""
  echo -e "${YELLOW}⚠ DNS zone still exists in Azure${NC}"
  echo "To delete it, run:"
  echo "  az network dns zone delete --resource-group $RESOURCE_GROUP --name $DNS_ZONE_NAME --yes"
fi

echo ""
echo -e "${GREEN}=== Cleanup Summary ===${NC}"
echo "✓ DNS zone removed from Terraform state"
if [ "$DELETE_FROM_AZURE" == "true" ]; then
  echo "✓ DNS zone deleted from Azure"
else
  echo "⚠ DNS zone still exists in Azure (use --delete-from-azure to delete)"
fi
echo ""
echo "Next steps:"
echo "1. Verify Terraform code has DNS zone resource commented out (already done in Phase 3)"
echo "2. Run 'terraform plan' to verify no changes needed"
echo "3. Run 'terraform apply' to ensure state is consistent"
