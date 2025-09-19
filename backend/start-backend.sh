#!/bin/bash

# Tru8 Backend Startup Script
# Starts Redis check, Celery worker, and FastAPI server

set -e  # Exit on any error

echo "======================================="
echo "    Tru8 Backend Startup Script"
echo "======================================="
echo

# Change to script directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}ERROR: Python not found${NC}"
    echo "Please install Python 3.8+ or add it to your PATH"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "[1/4] Checking Redis connection..."
if $PYTHON_CMD -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('✓ Redis is running')" 2>/dev/null; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${YELLOW}⚠ Redis not running. You need to start Redis:${NC}"
    echo "  Option 1: brew install redis && brew services start redis (macOS)"
    echo "  Option 2: sudo apt-get install redis-server (Ubuntu)"
    echo "  Option 3: docker run -d -p 6379:6379 redis:alpine"
    echo
    echo "Press Enter to continue anyway (some features may not work)..."
    read -r
fi

# Check if virtual environment should be activated
if [ -f "venv/bin/activate" ]; then
    echo "[2/4] Activating virtual environment..."
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
elif [ -f ".venv/bin/activate" ]; then
    echo "[2/4] Activating virtual environment..."
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo "[2/4] No virtual environment found, using system Python"
fi

# Install dependencies if needed
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}⚠ requirements.txt not found, skipping dependency check${NC}"
else
    echo "[3/4] Checking dependencies..."
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies checked${NC}"
fi

echo "[4/4] Starting services..."
echo
echo "======================================="
echo "  Starting Tru8 Backend Services"
echo "======================================="
echo
echo -e "${GREEN}✓ FastAPI will start on: http://localhost:8000${NC}"
echo -e "${GREEN}✓ API docs available at: http://localhost:8000/api/docs${NC}"
echo -e "${GREEN}✓ Celery worker will handle fact-checking tasks${NC}"
echo
echo "Press Ctrl+C to stop all services"
echo

# Function to cleanup background processes
cleanup() {
    echo
    echo "Shutting down services..."
    if [ ! -z "$CELERY_PID" ]; then
        kill $CELERY_PID 2>/dev/null || true
        echo "✓ Celery worker stopped"
    fi
    echo "✓ FastAPI server stopped"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Start Celery worker in background
echo "Starting Celery worker..."
# CRITICAL: Limit to 2 workers to prevent memory exhaustion (defaults to CPU count)
# On Linux/Mac we can use prefork, but on Windows use solo pool
celery -A app.workers worker --concurrency=2 --loglevel=info --logfile=celery.log &
CELERY_PID=$!
echo "[Memory Safe] Using only 2 Celery workers"

# Wait a moment for worker to start
sleep 2

# Start FastAPI server (this will block)
echo "Starting FastAPI server..."
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# If we get here, uvicorn exited, so cleanup
cleanup