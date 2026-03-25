#!/bin/bash
set -e

echo "=== Tru8 API Container Startup ==="

echo "Running database migrations..."
cd /app

# Ensure base tables exist (SQLModel create_all for fresh databases).
# Alembic migrations add columns/indexes to existing tables but don't
# create the initial schema. This is idempotent — does nothing if
# tables already exist.
python -c "
import asyncio
from app.core.database import engine
from sqlmodel import SQLModel
from app.models import *  # Import all models

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    await engine.dispose()

asyncio.run(init())
print('Base tables ensured.')
" || echo "WARNING: Base table creation failed, migrations may handle it."

# env.py handles async driver detection — pass DATABASE_URL as-is
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
