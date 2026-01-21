#!/bin/bash
# Script to trigger the Container App Job to grant database roles
# This is easier than using Azure Portal or CLI manually
#
# Usage: ./trigger-db-role-grant-job.sh <environment>
# Example: ./trigger-db-role-grant-job.sh dev

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Environment not provided${NC}"
    echo "Usage: $0 <environment>"
    echo "Example: $0 dev"
    exit 1
fi

ENVIRONMENT=$1
PROJECT_NAME="lexiqai"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"
JOB_NAME="${PROJECT_NAME}-init-grant-db-roles-${ENVIRONMENT}"

echo -e "${GREEN}=== Trigger Container App Job: Grant Database Roles ===${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Job Name: $JOB_NAME"
echo ""

# Check if Azure CLI is available
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not found${NC}"
    echo "Please install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Please log in...${NC}"
    az login
fi

# Check if job exists
echo -e "${YELLOW}Checking if job exists...${NC}"
if ! az containerapp job show --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo -e "${RED}Error: Container App Job not found: $JOB_NAME${NC}"
    echo ""
    echo "The job may not have been created yet. Please run:"
    echo "  cd infra/terraform"
    echo "  terraform apply"
    exit 1
fi

echo -e "${GREEN}✓ Job found${NC}"
echo ""

# Start the job
echo -e "${YELLOW}Starting job...${NC}"
az containerapp job start \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Job started successfully!${NC}"
    echo ""
    echo "Monitoring execution..."
    echo ""
    
    # Wait a moment for execution to start
    sleep 3
    
    # Get execution status
    EXECUTION=$(az containerapp job execution list \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].{Name:name,Status:properties.status,StartTime:properties.startTime}" \
        --output json 2>/dev/null || echo "{}")
    
    if [ "$EXECUTION" != "{}" ]; then
        EXECUTION_NAME=$(echo "$EXECUTION" | jq -r '.Name')
        STATUS=$(echo "$EXECUTION" | jq -r '.Status')
        
        echo "Execution: $EXECUTION_NAME"
        echo "Status: $STATUS"
        echo ""
        
        if [ "$STATUS" == "Running" ] || [ "$STATUS" == "Processing" ]; then
            echo -e "${YELLOW}Job is running...${NC}"
            echo ""
            echo "To view logs in real-time:"
            echo "  az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP --follow"
            echo ""
            echo "To check status:"
            echo "  az containerapp job execution show --name $JOB_NAME --resource-group $RESOURCE_GROUP --job-execution-name $EXECUTION_NAME"
        fi
    else
        echo -e "${YELLOW}Execution details not available yet.${NC}"
        echo ""
        echo "To check status manually:"
        echo "  az containerapp job execution list --name $JOB_NAME --resource-group $RESOURCE_GROUP"
    fi
    
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Wait for the job to complete (usually < 1 minute)"
    echo "2. Check logs to verify roles were granted:"
    echo "   az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP"
    echo "3. Verify your Container Apps can now connect to the database"
else
    echo ""
    echo -e "${RED}✗ Failed to start job${NC}"
    echo "Please check the error messages above"
    exit 1
fi
