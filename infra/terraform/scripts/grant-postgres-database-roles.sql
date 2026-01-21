-- Grant Database Roles to Managed Identity
-- This script grants the necessary database roles to the Managed Identity
-- so that services can connect to and use the PostgreSQL database
--
-- Usage Options:
--
-- Option 1: Use the shell script (RECOMMENDED - auto-populates identity name):
--   ./grant-postgres-database-roles.sh <environment>
--
-- Option 2: Set identity name via psql variable:
--   psql ... -v identity_name="lexiqai-identity-dev" -f grant-postgres-database-roles.sql
--
-- Option 3: Get identity name from Terraform and set manually:
--   IDENTITY_NAME=$(terraform output -raw identity_name)
--   psql ... -v identity_name="$IDENTITY_NAME" -f grant-postgres-database-roles.sql
--
-- Option 4: Set manually in psql:
--   \set identity_name 'lexiqai-identity-dev'
--   \i grant-postgres-database-roles.sql
--
-- Note: Identity name format: <project-name>-identity-<environment>
--   - Dev: lexiqai-identity-dev
--   - Staging: lexiqai-identity-staging
--   - Prod: lexiqai-identity-prod

-- Set identity name (can be overridden via -v identity_name="..." when calling psql)
\if :{?identity_name}
  -- Identity name already set via psql variable
\else
  -- Default placeholder (will fail - must be set via one of the options above)
  \set identity_name '<identity-name>'
  \echo 'ERROR: identity_name variable not set!'
  \echo 'Please use one of the usage options documented above.'
  \echo 'Or set it manually: \\set identity_name ''lexiqai-identity-dev'''
  \quit
\endif

-- Connect to the database
\c lexiqai

-- Create Azure AD user from Managed Identity
-- This creates a database user that maps to the Managed Identity
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = :'identity_name'
    ) THEN
        EXECUTE format('CREATE USER %I FROM EXTERNAL PROVIDER', :'identity_name');
        RAISE NOTICE 'Created Azure AD user: %', :'identity_name';
    ELSE
        RAISE NOTICE 'Azure AD user already exists: %', :'identity_name';
    END IF;
END
$$;

-- Grant database roles
-- db_datareader: Read data from all tables
-- db_datawriter: Insert, update, delete data in all tables
-- db_ddladmin: Create, alter, drop database objects (for migrations)
ALTER ROLE :identity_name GRANT db_datareader;
ALTER ROLE :identity_name GRANT db_datawriter;
ALTER ROLE :identity_name GRANT db_ddladmin;

-- Verify the grants
\du :identity_name

-- Show current user and database
SELECT current_user, current_database();

RAISE NOTICE 'Database roles granted successfully to: %', :'identity_name';
RAISE NOTICE 'The Managed Identity can now connect to the database using Azure AD authentication';
