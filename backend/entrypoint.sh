#!/bin/bash
set -e

echo "=== Tru8 API Container Startup ==="

# Download models to persistent volume if not already cached
# Pass the command ($1) so the script can detect if this is worker or web
echo "Checking ML model cache..."
python scripts/download_models.py "$1"

echo "Starting application..."

# Execute the main command (uvicorn or celery)
exec "$@"
