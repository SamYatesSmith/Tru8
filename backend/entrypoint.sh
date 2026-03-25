#!/bin/bash
set -e

echo "=== Tru8 API Container Startup ==="

echo "Running database migrations..."
cd /app
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
