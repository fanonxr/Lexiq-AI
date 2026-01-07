#!/usr/bin/env python3
"""
Reset database by truncating all tables while preserving schema.

This script:
1. Connects to the database
2. Truncates all tables (deletes all rows)
3. Preserves the schema structure (tables, columns, indexes, constraints)

Usage:
    python scripts/reset_database.py
    # Or with DATABASE_URL environment variable:
    DATABASE_URL="postgresql://user:pass@host:port/db" python scripts/reset_database.py
"""

import asyncio
import os
import sys
from typing import List

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add api-core src directory to path to import api_core modules
# Script is in tools/scripts/, need to go up to root, then into apps/api-core/src
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..", "..")
api_core_src = os.path.join(project_root, "apps", "api-core", "src")
sys.path.insert(0, api_core_src)

from api_core.config import get_settings


async def get_all_table_names(engine) -> List[str]:
    """Get all table names from the database."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
        )
        tables = [row[0] for row in result]
        return tables


async def truncate_all_tables(engine) -> None:
    """Truncate all tables in the database."""
    tables = await get_all_table_names(engine)
    
    if not tables:
        print("No tables found in the database.")
        return
    
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    
    print("\n⚠️  WARNING: This will delete ALL data from ALL tables!")
    print("The schema (tables, columns, indexes, constraints) will be preserved.")
    print(f"Tables to be truncated: {', '.join(tables)}")
    
    # Confirm action
    response = input("\nAre you sure you want to proceed? (yes/no): ")
    if response.lower() != "yes":
        print("Operation cancelled.")
        return
    
    async with engine.begin() as conn:
        # PostgreSQL TRUNCATE automatically clears:
        # - All data rows
        # - All index entries (indexes are just pointers to data)
        # - Resets sequences (with RESTART IDENTITY)
        # - Handles foreign keys (with CASCADE)
        print("\nTruncating tables...")
        print("   (This will clear all data, index entries, and reset sequences)")
        
        # Build TRUNCATE statement with CASCADE to handle foreign keys
        # RESTART IDENTITY resets auto-increment sequences
        # CASCADE truncates dependent tables automatically
        table_names = ", ".join(f'"{table}"' for table in tables)
        truncate_sql = f'TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;'
        
        try:
            await conn.execute(text(truncate_sql))
            # The transaction is automatically committed when exiting the 'begin' context
            print("✓ Successfully truncated all tables")
            print("   (Index entries are automatically cleared - no need to reset them separately)")
        except Exception as e:
            print(f"✗ Error truncating tables: {e}")
            raise
    
    # Verify tables are empty
    print("\nVerifying tables are empty...")
    async with engine.connect() as conn:
        all_empty = True
        for table in tables:
            result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}";'))
            count = result.scalar()
            if count > 0:
                print(f"⚠️  Warning: Table '{table}' still has {count} rows")
                all_empty = False
                # Show sample data for non-empty tables
                if table == "users":
                    sample_result = await conn.execute(text(f'SELECT id, email, name FROM "{table}" LIMIT 5;'))
                    samples = sample_result.fetchall()
                    print(f"   Sample users: {samples}")
            else:
                print(f"✓ Table '{table}' is empty")
        
        if not all_empty:
            print("\n⚠️  WARNING: Some tables still contain data!")
            print("The TRUNCATE may have failed. Try running the reset again.")
            return
    
    print("\n✓ Database reset complete! All tables are empty but schema is preserved.")


async def main():
    """Main function."""
    settings = get_settings()
    
    # Get DATABASE_URL from environment or use settings
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        if not settings.database.url:
            print("Error: DATABASE_URL environment variable is not set")
            print("Usage: DATABASE_URL='postgresql://user:pass@host:port/db' python scripts/reset_database.py")
            sys.exit(1)
        database_url = settings.database.url
    
    # Convert postgresql:// to postgresql+asyncpg:// for SQLAlchemy async
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        print("Error: DATABASE_URL must be a PostgreSQL connection string")
        sys.exit(1)
    
    print(f"Connecting to database...")
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")
    
    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
        
        # Test connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        
        print("✓ Connected to database")
        
        # Truncate all tables
        await truncate_all_tables(engine)
        
        await engine.dispose()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

