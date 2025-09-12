# Tru8 Backend Startup Guide

## Quick Start

### Windows
```bash
cd backend
.\start-backend.bat
```

### Linux/macOS
```bash
cd backend
./start-backend.sh
```

## What the Startup Script Does

1. **Checks Dependencies**: Ensures Python and Redis are available
2. **Activates Virtual Environment**: If `venv/` or `.venv/` exists
3. **Installs Dependencies**: Updates packages from `requirements.txt`
4. **Starts Celery Worker**: Processes fact-checking tasks in background
5. **Starts FastAPI Server**: Main API server with auto-reload

## Services Started

- **FastAPI Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Celery Worker**: Background task processing
- **Redis**: Required for Celery (must be running separately)

## Prerequisites

### Required
- **Python 3.8+**: Must be in PATH
- **Redis Server**: Must be running on localhost:6379

### Redis Installation Options

**Option 1 - Docker (Recommended)**
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

**Option 2 - Windows**
- Download Redis for Windows
- Or use WSL with Redis

**Option 3 - macOS**
```bash
brew install redis
brew services start redis
```

**Option 4 - Ubuntu/Linux**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

## Manual Startup (Alternative)

If you prefer to start services manually:

```bash
# Terminal 1 - Start Redis (if not already running)
redis-server

# Terminal 2 - Start Celery Worker  
cd backend
celery -A app.workers worker --loglevel=info

# Terminal 3 - Start FastAPI Server
cd backend
uvicorn main:app --reload
```

## Troubleshooting

### "Redis not running" Error
- Start Redis server first (see installation options above)
- Verify Redis is running: `redis-cli ping` should return `PONG`

### "Python not found" Error  
- Install Python 3.8+ and add to PATH
- Or activate your virtual environment first

### "celery command not found" Error
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the correct directory

### Port Already in Use
- **Port 8000**: Another FastAPI server is running
- **Port 6379**: Another Redis instance is running
- Use `netstat -an | findstr :8000` (Windows) or `lsof -i :8000` (Linux/macOS)

## Logs

- **FastAPI**: Displayed in console
- **Celery Worker**: Saved to `celery.log` file
- **Redis**: Check Redis logs if connection issues

## Stopping Services

Press **Ctrl+C** in the terminal running the startup script. This will gracefully shut down both FastAPI and Celery worker.

## Production Notes

For production deployment, consider:
- Using proper process managers (systemd, supervisord)
- Setting up Redis persistence
- Configuring proper logging
- Using environment-specific settings