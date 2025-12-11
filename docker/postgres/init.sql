-- PostgreSQL Initialization Script
-- This script runs automatically when the PostgreSQL container is first created
-- It sets up the initial database schema and any required configurations

-- Create the main database (if not already created by POSTGRES_DB env var)
-- Note: The database is created automatically by the postgres image using POSTGRES_DB
-- This script is for additional setup

-- Grant necessary permissions
-- (The postgres user already has full permissions)

-- Create extensions that might be needed (but not pgvector - Qdrant handles vectors)
-- Example: uuid extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial schema placeholder
-- This will be replaced by Alembic migrations in the application
-- DO NOT create tables here - use migrations instead

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'LexiqAI PostgreSQL database initialized successfully';
    RAISE NOTICE 'Database: %', current_database();
    RAISE NOTICE 'User: %', current_user;
END $$;

