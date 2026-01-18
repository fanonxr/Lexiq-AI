#!/bin/bash
# Script to configure Static Web App app settings and get deployment token
# Usage: ./setup-static-web-app.sh <environment>
# Example: ./setup-static-web-app.sh dev

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
  echo -e "${RED}Error: Environment is required${NC}"
  echo "Usage: $0 <environment>"
  echo "Example: $0 dev"
  exit 1
fi

ENVIRONMENT=$1
PROJECT_NAME="lexiqai"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"
SWA_NAME="${PROJECT_NAME}-web-${ENVIRONMENT}"

echo -e "${GREEN}=== Static Web App Setup Script ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Static Web App: $SWA_NAME"
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

# Verify Static Web App exists
echo -e "${YELLOW}Checking Static Web App...${NC}"
if ! az staticwebapp show --name "$SWA_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
  echo -e "${RED}Error: Static Web App '$SWA_NAME' not found${NC}"
  echo "Create it first with Terraform:"
  echo "  cd infra/terraform"
  echo "  terraform apply -var-file=${ENVIRONMENT}.tfvars"
  exit 1
fi
echo -e "${GREEN}✓ Static Web App found${NC}"

# Get Static Web App details
echo ""
echo -e "${YELLOW}Getting Static Web App details...${NC}"
DEFAULT_HOSTNAME=$(az staticwebapp show \
  --name "$SWA_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "defaultHostname" -o tsv)

API_KEY=$(az staticwebapp secrets list \
  --name "$SWA_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.apiKey" -o tsv)

echo -e "${GREEN}✓ Static Web App details retrieved${NC}"
echo "  Default hostname: $DEFAULT_HOSTNAME"
echo "  API key: ${API_KEY:0:10}... (hidden)"
echo ""

# Get API Core URL from Terraform output (if available)
echo -e "${YELLOW}Getting API Core URL...${NC}"
cd "$(dirname "$0")/.."
if terraform output -json api_core_url &> /dev/null; then
  API_CORE_URL=$(terraform output -raw api_core_url 2>/dev/null || echo "")
  echo "  API Core URL: ${API_CORE_URL:-'(not set)'}"
else
  API_CORE_URL=""
  echo "  API Core URL: (not available - run 'terraform output' to get it)"
fi
echo ""

# Get Azure AD values from Terraform output (if available)
echo -e "${YELLOW}Getting Azure AD configuration...${NC}"
TENANT_ID=$(terraform output -raw azure_ad_tenant_id 2>/dev/null || echo "")
CLIENT_ID=$(terraform output -raw azure_ad_application_id 2>/dev/null || echo "")
AUTHORITY_URL=$(terraform output -raw azure_ad_authority_url 2>/dev/null || echo "https://login.microsoftonline.com/common")

if [ -n "$TENANT_ID" ]; then
  echo "  Tenant ID: $TENANT_ID"
else
  echo "  Tenant ID: (not available - set manually)"
fi

if [ -n "$CLIENT_ID" ]; then
  echo "  Client ID: $CLIENT_ID"
else
  echo "  Client ID: (not available - set manually)"
fi

echo "  Authority URL: $AUTHORITY_URL"
echo ""

# Determine Static Web App URL
if [ -n "$DEFAULT_HOSTNAME" ]; then
  SWA_URL="https://${DEFAULT_HOSTNAME}"
else
  SWA_URL=""
fi

# Configure app settings
echo -e "${YELLOW}Configuring app settings...${NC}"

# Build app settings command
APP_SETTINGS=()

if [ -n "$TENANT_ID" ]; then
  APP_SETTINGS+=("NEXT_PUBLIC_ENTRA_ID_TENANT_ID=$TENANT_ID")
fi

if [ -n "$CLIENT_ID" ]; then
  APP_SETTINGS+=("NEXT_PUBLIC_ENTRA_ID_CLIENT_ID=$CLIENT_ID")
fi

if [ -n "$AUTHORITY_URL" ]; then
  APP_SETTINGS+=("NEXT_PUBLIC_ENTRA_ID_AUTHORITY=$AUTHORITY_URL")
fi

if [ -n "$SWA_URL" ]; then
  APP_SETTINGS+=("NEXT_PUBLIC_APP_URL=$SWA_URL")
fi

if [ -n "$API_CORE_URL" ]; then
  APP_SETTINGS+=("NEXT_PUBLIC_API_URL=$API_CORE_URL")
fi

# Add default feature flags
APP_SETTINGS+=("NEXT_PUBLIC_ENABLE_GOOGLE_SIGNIN=true")
APP_SETTINGS+=("NEXT_PUBLIC_ENABLE_EMAIL_OTP=true")
APP_SETTINGS+=("NODE_ENV=production")

# Set app settings
if [ ${#APP_SETTINGS[@]} -gt 0 ]; then
  SETTINGS_STRING=$(IFS=' '; echo "${APP_SETTINGS[*]}")
  
  echo "Setting app settings:"
  for setting in "${APP_SETTINGS[@]}"; do
    echo "  - $setting"
  done
  echo ""
  
  if az staticwebapp appsettings set \
    --name "$SWA_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --setting-names $SETTINGS_STRING &> /dev/null; then
    echo -e "${GREEN}✓ App settings configured${NC}"
  else
    echo -e "${YELLOW}⚠ Failed to set app settings via CLI${NC}"
    echo "You can set them manually in Azure Portal:"
    echo "  https://portal.azure.com/#@/resource/subscriptions/.../staticSites/$SWA_NAME/configuration"
  fi
else
  echo -e "${YELLOW}⚠ No app settings to configure (values not available)${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup Summary ===${NC}"
echo "Static Web App: $SWA_NAME"
echo "Default hostname: $DEFAULT_HOSTNAME"
echo "URL: $SWA_URL"
echo ""

# Output GitHub secret instructions
echo -e "${YELLOW}=== GitHub Secrets Setup ===${NC}"
echo "Add the following secrets to your GitHub repository:"
echo ""
echo "1. Go to: GitHub → Settings → Secrets and variables → Actions"
echo ""
echo "2. Add these secrets:"
echo ""
echo "   Name: AZURE_STATIC_WEB_APPS_API_TOKEN"
echo "   Value: $API_KEY"
echo ""
echo "   Name: NEXT_PUBLIC_ENTRA_ID_TENANT_ID"
echo "   Value: ${TENANT_ID:-'(get from Terraform output: terraform output azure_ad_tenant_id)'}"
echo ""
echo "   Name: NEXT_PUBLIC_ENTRA_ID_CLIENT_ID"
echo "   Value: ${CLIENT_ID:-'(get from Terraform output: terraform output azure_ad_application_id)'}"
echo ""
echo "   Name: NEXT_PUBLIC_ENTRA_ID_AUTHORITY"
echo "   Value: $AUTHORITY_URL"
echo ""
echo "   Name: NEXT_PUBLIC_APP_URL"
echo "   Value: $SWA_URL"
echo ""
if [ -n "$API_CORE_URL" ]; then
  echo "   Name: NEXT_PUBLIC_API_URL"
  echo "   Value: $API_CORE_URL"
else
  echo "   Name: NEXT_PUBLIC_API_URL"
  echo "   Value: (get from Terraform output: terraform output api_core_url)"
fi
echo ""
echo "   Name: NEXT_PUBLIC_ENABLE_GOOGLE_SIGNIN"
echo "   Value: true"
echo ""
echo "   Name: NEXT_PUBLIC_ENABLE_EMAIL_OTP"
echo "   Value: true"
echo ""

echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Add GitHub secrets (see above)"
echo "2. Push to develop branch to trigger deployment"
echo "3. Check GitHub Actions workflow for deployment status"
