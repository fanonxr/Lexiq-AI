#!/bin/bash
# Script to grant database roles to Managed Identity after Terraform applies
# This script automates the process of granting database roles to the Managed Identity
#
# Usage: ./grant-postgres-database-roles.sh <environment> [server-name] [admin-username]
# Example: ./grant-postgres-database-roles.sh dev

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if environment is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Environment not provided${NC}"
    echo "Usage: $0 <environment> [server-name] [admin-username]"
    echo "Example: $0 dev"
    exit 1
fi

ENVIRONMENT=$1
PROJECT_NAME="lexiqai"

# Get server name if not provided
if [ -z "$2" ]; then
    SERVER_NAME="${PROJECT_NAME}-db-${ENVIRONMENT}"
else
    SERVER_NAME=$2
fi

# Get admin username if not provided
if [ -z "$3" ]; then
    ADMIN_USERNAME="${PROJECT_NAME}-admin"
else
    ADMIN_USERNAME=$3
fi

# Get identity name (format: <project-name>-identity-<environment>)
# Examples:
#   - Dev: lexiqai-identity-dev
#   - Staging: lexiqai-identity-staging
#   - Prod: lexiqai-identity-prod
IDENTITY_NAME="${PROJECT_NAME}-identity-${ENVIRONMENT}"

echo -e "${GREEN}=== Grant PostgreSQL Database Roles to Managed Identity ===${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Server Name: $SERVER_NAME"
echo "Identity Name: $IDENTITY_NAME"
echo "Admin Username: $ADMIN_USERNAME"
echo ""

# Get server FQDN
echo -e "${YELLOW}Getting PostgreSQL server FQDN...${NC}"
SERVER_FQDN=$(az postgres flexible-server show \
    --name "$SERVER_NAME" \
    --resource-group "${PROJECT_NAME}-rg-${ENVIRONMENT}" \
    --query "fullyQualifiedDomainName" \
    --output tsv 2>/dev/null || echo "")

if [ -z "$SERVER_FQDN" ]; then
    echo -e "${RED}Error: Could not find PostgreSQL server: $SERVER_NAME${NC}"
    echo "Please check the server name and resource group"
    exit 1
fi

echo -e "${GREEN}✓ Server FQDN: $SERVER_FQDN${NC}"
echo ""

# Get database password from Key Vault or prompt
echo -e "${YELLOW}Getting database password...${NC}"
KEY_VAULT_NAME="${PROJECT_NAME}-kv-${ENVIRONMENT}"

if az keyvault secret show --name "postgres-admin-password" --vault-name "$KEY_VAULT_NAME" &>/dev/null; then
    DB_PASSWORD=$(az keyvault secret show \
        --name "postgres-admin-password" \
        --vault-name "$KEY_VAULT_NAME" \
        --query "value" \
        --output tsv)
    echo -e "${GREEN}✓ Password retrieved from Key Vault${NC}"
else
    echo -e "${YELLOW}Password not found in Key Vault. Please enter it manually:${NC}"
    read -s DB_PASSWORD
    echo ""
fi

# Create SQL script with identity name
SQL_SCRIPT=$(cat <<EOF
-- Grant Database Roles to Managed Identity
\c lexiqai

-- Create Azure AD user from Managed Identity
DO \$\$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = '$IDENTITY_NAME'
    ) THEN
        EXECUTE format('CREATE USER %I FROM EXTERNAL PROVIDER', '$IDENTITY_NAME');
        RAISE NOTICE 'Created Azure AD user: $IDENTITY_NAME';
    ELSE
        RAISE NOTICE 'Azure AD user already exists: $IDENTITY_NAME';
    END IF;
END
\$\$;

-- Grant database roles
ALTER ROLE "$IDENTITY_NAME" GRANT db_datareader;
ALTER ROLE "$IDENTITY_NAME" GRANT db_datawriter;
ALTER ROLE "$IDENTITY_NAME" GRANT db_ddladmin;

-- Verify the grants
\du "$IDENTITY_NAME"

SELECT 'Database roles granted successfully to: $IDENTITY_NAME' AS message;
EOF
)

echo -e "${YELLOW}Granting database roles...${NC}"
echo ""

# Execute SQL script using psql
PGPASSWORD="$DB_PASSWORD" psql \
    "host=$SERVER_FQDN port=5432 dbname=lexiqai user=$ADMIN_USERNAME sslmode=require" \
    -c "$SQL_SCRIPT"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Database roles granted successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Identity Name Used:${NC}"
    echo "  $IDENTITY_NAME"
    echo ""
    echo -e "${YELLOW}Note:${NC} Identity name format is: <project-name>-identity-<environment>"
    echo "  - Each environment has a different identity name"
    echo "  - Dev: ${PROJECT_NAME}-identity-dev"
    echo "  - Staging: ${PROJECT_NAME}-identity-staging"
    echo "  - Prod: ${PROJECT_NAME}-identity-prod"
    echo ""
    echo "The Managed Identity '$IDENTITY_NAME' can now:"
    echo "  - Read data from all tables (db_datareader)"
    echo "  - Insert, update, delete data (db_datawriter)"
    echo "  - Create, alter, drop database objects (db_ddladmin)"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Update connection strings in Container Apps to use Azure AD authentication"
    echo "2. Test database connectivity from Container Apps"
else
    echo ""
    echo -e "${RED}✗ Failed to grant database roles${NC}"
    echo "Please check the error messages above"
    exit 1
fi
