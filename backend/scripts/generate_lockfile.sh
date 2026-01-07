#!/bin/bash
# Generate requirements.lock for reproducible builds
# Run this from the backend directory after installing dependencies

set -e

echo "Generating requirements.lock..."

# Ensure we're in a virtual environment or have dependencies installed
if ! pip show fastapi > /dev/null 2>&1; then
    echo "Error: Dependencies not installed. Run 'pip install -r requirements.txt' first."
    exit 1
fi

# Generate lock file
pip freeze > requirements.lock

echo "Generated requirements.lock with $(wc -l < requirements.lock) packages"
echo ""
echo "To use in Dockerfile, update:"
echo "  COPY requirements.lock ."
echo "  RUN pip install --no-cache-dir -r requirements.lock"
