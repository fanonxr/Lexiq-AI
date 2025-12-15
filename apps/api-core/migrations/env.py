"""Alembic environment configuration."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import your application's Base and models
# This ensures Alembic can detect all models for autogenerate
import sys
from pathlib import Path

# Add the src directory to the path so we can import api_core
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Import models for autogenerate
from api_core.database.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from application settings (environment variables)
# Try to get from settings, fallback to environment variable or alembic.ini
try:
    from api_core.config import get_settings
    
    settings = get_settings()
    database_url = settings.database.url
    
    # Convert async URL to sync URL for Alembic
    # Alembic uses synchronous connections (psycopg2), not async (asyncpg)
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        # Keep as is - Alembic will use psycopg2 by default
        pass
    
    # Override the sqlalchemy.url from alembic.ini with the one from settings
    config.set_main_option("sqlalchemy.url", database_url)
except Exception as e:
    # Fallback: use DATABASE_URL from environment or alembic.ini
    import os
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Convert async URL to sync URL for Alembic
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        config.set_main_option("sqlalchemy.url", database_url)
    # If no DATABASE_URL, alembic.ini will be used (which has a placeholder)
    pass

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
