#!/bin/bash
set -e

echo "=== Tru8 API Container Startup ==="

echo "Running database migrations..."
cd /app

# Ensure base tables exist and Alembic state is consistent.
# On a fresh database: create_all builds all tables from current models,
# then stamp Alembic to HEAD so it doesn't try to re-run old migrations.
# On an existing database: create_all is a no-op, Alembic runs normally.
python -c "
import asyncio
from app.core.database import engine
from sqlmodel import SQLModel
from app.models import *

async def init():
    from sqlalchemy import text, inspect

    async with engine.begin() as conn:
        # Check if alembic_version table exists (= existing database)
        def check_alembic(sync_conn):
            insp = inspect(sync_conn)
            return 'alembic_version' in insp.get_table_names()

        has_alembic = await conn.run_sync(check_alembic)

        if not has_alembic:
            # Fresh database — create all tables from models
            await conn.run_sync(SQLModel.metadata.create_all)
            print('Fresh database: base tables created.')
        else:
            print('Existing database: tables already present.')

    await engine.dispose()
    return has_alembic

has_alembic = asyncio.run(init())

if not has_alembic:
    # Stamp Alembic to HEAD — tables were created with current schema,
    # so all migrations are already represented.
    import subprocess
    subprocess.run(['python', '-m', 'alembic', 'stamp', 'head'], check=True)
    print('Alembic stamped to HEAD.')
" || echo "WARNING: Base table setup failed, attempting migrations anyway."

# Run any pending migrations (no-op if just stamped to HEAD)
python -m alembic upgrade head || {
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "ERROR: Migration failed in production. Aborting startup."
        exit 1
    else
        echo "WARNING: Migration failed (database may not be ready yet). Continuing..."
    fi
}

echo "Checking ML model cache..."
python scripts/download_models.py

echo "Starting application on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
