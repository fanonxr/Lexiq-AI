#!/bin/bash
# Generic script to trigger any Container App Init Job
# 
# Usage: ./trigger-init-job.sh <environment> <job-type>
# Examples:
#   ./trigger-init-job.sh dev grant-db-roles
#   ./trigger-init-job.sh dev db-migration
#   ./trigger-init-job.sh prod multi-region-setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}Error: Missing required arguments${NC}"
    echo ""
    echo "Usage: $0 <environment> <job-type>"
    echo ""
    echo "Examples:"
    echo "  $0 dev grant-db-roles"
    echo "  $0 dev db-migration"
    echo "  $0 prod multi-region-setup"
    echo ""
    echo "Available job types:"
    echo "  - grant-db-roles      : Grant PostgreSQL database roles to Managed Identity"
    echo "  - db-migration        : Run database migrations (if configured)"
    echo "  - multi-region-setup  : Setup resources in secondary region (if configured)"
    echo "  - seed-data           : Seed initial data (if configured)"
    exit 1
fi

ENVIRONMENT=$1
JOB_TYPE=$2
PROJECT_NAME="lexiqai"
RESOURCE_GROUP="${PROJECT_NAME}-rg-${ENVIRONMENT}"
JOB_NAME="${PROJECT_NAME}-init-${JOB_TYPE}-${ENVIRONMENT}"

echo -e "${GREEN}=== Trigger Container App Init Job ===${NC}"
echo ""
echo -e "${BLUE}Environment:${NC} $ENVIRONMENT"
echo -e "${BLUE}Job Type:${NC}    $JOB_TYPE"
echo -e "${BLUE}Resource Group:${NC} $RESOURCE_GROUP"
echo -e "${BLUE}Job Name:${NC}    $JOB_NAME"
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
    echo "The job may not have been created yet. Please:"
    echo "  1. Run 'terraform apply' to create the job"
    echo "  2. Or check if the job type '$JOB_TYPE' is configured in Terraform"
    echo ""
    echo "Available jobs in this environment:"
    az containerapp job list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(name, 'init')].{Name:name,Status:properties.provisioningState}" \
        --output table 2>/dev/null || echo "  (No init jobs found)"
    exit 1
fi

echo -e "${GREEN}✓ Job found${NC}"
echo ""

# Show job details
echo -e "${YELLOW}Job Details:${NC}"
az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "{Name:name,Status:properties.provisioningState,TriggerType:properties.configuration.triggerType}" \
    --output table

echo ""

# Confirm before starting
read -p "Start this job? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

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
        EXECUTION_NAME=$(echo "$EXECUTION" | jq -r '.Name // empty')
        STATUS=$(echo "$EXECUTION" | jq -r '.Status // empty')
        
        if [ -n "$EXECUTION_NAME" ] && [ -n "$STATUS" ]; then
            echo -e "${BLUE}Execution:${NC} $EXECUTION_NAME"
            echo -e "${BLUE}Status:${NC} $STATUS"
            echo ""
            
            if [ "$STATUS" == "Running" ] || [ "$STATUS" == "Processing" ]; then
                echo -e "${YELLOW}Job is running...${NC}"
            fi
        fi
    fi
    
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Wait for the job to complete (usually < 1 minute)"
    echo "2. Check logs:"
    echo "   ${BLUE}az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP${NC}"
    echo "3. Check execution status:"
    echo "   ${BLUE}az containerapp job execution list --name $JOB_NAME --resource-group $RESOURCE_GROUP${NC}"
else
    echo ""
    echo -e "${RED}✗ Failed to start job${NC}"
    echo "Please check the error messages above"
    exit 1
fi
