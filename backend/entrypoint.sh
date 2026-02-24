#!/bin/bash
set -e

echo "=== Tru8 API Container Startup ==="

echo "Running database migrations..."
cd /app
python -m alembic upgrade head || {
    echo "WARNING: Migration failed (database may not be ready yet). Continuing..."
}

echo "Checking ML model cache..."
python scripts/download_models.py

echo "Starting application..."
exec "$@"
