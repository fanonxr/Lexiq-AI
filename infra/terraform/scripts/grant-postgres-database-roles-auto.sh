#!/bin/bash
# Auto-generate SQL script with identity name populated
# This script generates a SQL file with the identity name already filled in
#
# Usage: ./grant-postgres-database-roles-auto.sh <environment>
# Example: ./grant-postgres-database-roles-auto.sh dev

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
IDENTITY_NAME="${PROJECT_NAME}-identity-${ENVIRONMENT}"

echo -e "${GREEN}=== Generate SQL Script with Identity Name ===${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Identity Name: $IDENTITY_NAME"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_TEMPLATE="${SCRIPT_DIR}/grant-postgres-database-roles.sql"
SQL_OUTPUT="${SCRIPT_DIR}/grant-postgres-database-roles-${ENVIRONMENT}.sql"

# Check if template exists
if [ ! -f "$SQL_TEMPLATE" ]; then
    echo -e "${RED}Error: SQL template not found: $SQL_TEMPLATE${NC}"
    exit 1
fi

# Generate SQL with identity name populated
echo -e "${YELLOW}Generating SQL script with identity name: $IDENTITY_NAME${NC}"

# Create SQL file with identity name replaced
cat > "$SQL_OUTPUT" <<SQL
-- Grant Database Roles to Managed Identity
-- Auto-generated for environment: $ENVIRONMENT
-- Identity Name: $IDENTITY_NAME
-- Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

-- Connect to the database
\c lexiqai

-- Create Azure AD user from Managed Identity
-- This creates a database user that maps to the Managed Identity
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
-- db_datareader: Read data from all tables
-- db_datawriter: Insert, update, delete data in all tables
-- db_ddladmin: Create, alter, drop database objects (for migrations)
ALTER ROLE "$IDENTITY_NAME" GRANT db_datareader;
ALTER ROLE "$IDENTITY_NAME" GRANT db_datawriter;
ALTER ROLE "$IDENTITY_NAME" GRANT db_ddladmin;

-- Verify the grants
\du "$IDENTITY_NAME"

-- Show current user and database
SELECT current_user, current_database();

SELECT 'Database roles granted successfully to: $IDENTITY_NAME' AS message;
SQL

echo -e "${GREEN}✓ SQL script generated: $SQL_OUTPUT${NC}"
echo ""
echo "You can now run this script with:"
echo "  psql \"host=<server-fqdn> port=5432 dbname=lexiqai user=<admin-username> sslmode=require\" -f $SQL_OUTPUT"
echo ""
echo "Or use the full automation script:"
echo "  ./grant-postgres-database-roles.sh $ENVIRONMENT"
