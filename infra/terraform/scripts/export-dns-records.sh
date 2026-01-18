#!/bin/bash
# Script to export DNS records from environment-specific DNS zone
# Usage: ./export-dns-records.sh <environment> [dns-zone-name] [output-file]
# Example: ./export-dns-records.sh dev lexiqai.com dns-records-dev.json

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
  echo -e "${RED}Error: Environment is required${NC}"
  echo "Usage: $0 <environment> [dns-zone-name] [output-file]"
  echo "Example: $0 dev lexiqai.com dns-records-dev.json"
  exit 1
fi

ENVIRONMENT=$1
DNS_ZONE_NAME=${2:-""}
OUTPUT_FILE=${3:-"dns-records-${ENVIRONMENT}.json"}
PROJECT_NAME="lexiqai"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"

echo -e "${GREEN}=== DNS Records Export Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Output File: $OUTPUT_FILE"
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

# Verify DNS zone exists
echo -e "${YELLOW}Checking DNS zone: $DNS_ZONE_NAME${NC}"
if ! az network dns zone show --resource-group "$RESOURCE_GROUP" --name "$DNS_ZONE_NAME" &> /dev/null; then
  echo -e "${RED}Error: DNS zone '$DNS_ZONE_NAME' not found in resource group '$RESOURCE_GROUP'${NC}"
  exit 1
fi
echo -e "${GREEN}✓ DNS zone found${NC}"

# Export all DNS records
echo ""
echo -e "${YELLOW}Exporting DNS records...${NC}"

# Export all record types
RECORDS=$(az network dns record-set list \
  --resource-group "$RESOURCE_GROUP" \
  --zone-name "$DNS_ZONE_NAME" \
  --output json)

if [ -z "$RECORDS" ] || [ "$RECORDS" == "[]" ]; then
  echo -e "${YELLOW}No DNS records found in zone${NC}"
  echo "{}" > "$OUTPUT_FILE"
else
  echo "$RECORDS" > "$OUTPUT_FILE"
  RECORD_COUNT=$(echo "$RECORDS" | jq '. | length' 2>/dev/null || echo "0")
  echo -e "${GREEN}✓ Exported $RECORD_COUNT DNS records${NC}"
fi

# Display summary
echo ""
echo -e "${GREEN}=== Export Summary ===${NC}"
echo "DNS Zone: $DNS_ZONE_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Output File: $OUTPUT_FILE"
echo ""

# Show record types found
if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
  if command -v jq &> /dev/null; then
    echo "Record types found:"
    jq -r '.[] | "\(.type) - \(.name)"' "$OUTPUT_FILE" 2>/dev/null | sort | uniq | sed 's/^/  - /' || echo "  (Unable to parse JSON)"
  else
    echo "Records exported to: $OUTPUT_FILE"
    echo "Install 'jq' for better JSON parsing"
  fi
fi

echo ""
echo -e "${GREEN}Export complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review the exported DNS records in: $OUTPUT_FILE"
echo "2. Import records to shared DNS zone (if using Azure DNS)"
echo "3. Update DNS name servers in your domain registrar (if using shared DNS zone)"
