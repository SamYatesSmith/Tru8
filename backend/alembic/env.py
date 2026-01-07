from logging.config import fileConfig
from sqlalchemy import pool, engine_from_config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import os

# Import your models here
from app.models import *  # This imports all models
from sqlmodel import SQLModel

# this is the Alembic Config object
config = context.config

# Get DATABASE_URL from environment (required for production)
# Falls back to a default for local development only
def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Fallback for local development (should not be used in production)
    return "postgresql+asyncpg://postgres:password@localhost:5433/tru8_dev"

# Override sqlalchemy.url with environment variable
config.set_main_option("sqlalchemy.url", get_database_url())

# Interpret the config file for Python logging
# Skip if logging sections are not configured
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except KeyError:
        # alembic.ini doesn't have logging config, skip it
        pass

# add your model's MetaData object here for 'autogenerate' support
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()