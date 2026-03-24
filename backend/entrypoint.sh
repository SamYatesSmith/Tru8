#!/bin/bash
set -e

echo "=== Tru8 API Container Startup ==="

echo "Running database migrations..."
cd /app
# Alembic needs sync driver — convert asyncpg URL to psycopg2 for migration
export ALEMBIC_DATABASE_URL="${DATABASE_URL//+asyncpg/}"
DATABASE_URL="$ALEMBIC_DATABASE_URL" python -m alembic upgrade head || {
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
