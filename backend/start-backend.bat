@echo off
echo =======================================
echo    Tru8 Backend Startup Script
echo =======================================
echo.

REM Change to backend directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Check if Redis is running
echo [1/4] Checking Redis connection...
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping(); print('✓ Redis is running')" 2>nul
if errorlevel 1 (
    echo ⚠ Redis not running. You need to start Redis manually:
    echo   Option 1: Install Redis for Windows
    echo   Option 2: Use Docker: docker run -d -p 6379:6379 redis:alpine
    echo   Option 3: Use WSL with Redis
    echo.
    echo Press any key to continue anyway ^(some features may not work^)...
    pause >nul
)

REM Check if virtual environment should be activated
if exist "venv\Scripts\activate.bat" (
    echo [2/4] Activating virtual environment...
    call venv\Scripts\activate.bat
    echo ✓ Virtual environment activated
) else if exist ".venv\Scripts\activate.bat" (
    echo [2/4] Activating virtual environment...
    call .venv\Scripts\activate.bat  
    echo ✓ Virtual environment activated
) else (
    echo [2/4] No virtual environment found, using system Python
)

REM Check and install only essential dependencies (avoid scikit-learn)
echo [3/4] Checking essential dependencies...
python -c "import celery" 2>nul
if errorlevel 1 (
    echo Installing Celery...
    pip install -q celery redis
)
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo Installing Uvicorn and FastAPI...
    pip install -q uvicorn fastapi python-multipart
)
python -c "import sentry_sdk" 2>nul
if errorlevel 1 (
    echo Installing Sentry SDK...
    pip install -q sentry-sdk
)
python -c "import sqlmodel" 2>nul
if errorlevel 1 (
    echo Installing SQLModel...
    pip install -q sqlmodel asyncpg
)
python -c "import httpx" 2>nul
if errorlevel 1 (
    echo Installing HTTPX...
    pip install -q httpx
)
python -c "import jwt" 2>nul
if errorlevel 1 (
    echo Installing PyJWT...
    pip install -q pyjwt cryptography
)
python -c "import prometheus_client" 2>nul
if errorlevel 1 (
    echo Installing Prometheus client...
    pip install -q prometheus-client
)
python -c "import aiofiles" 2>nul
if errorlevel 1 (
    echo Installing aiofiles...
    pip install -q aiofiles
)
python -c "import alembic" 2>nul
if errorlevel 1 (
    echo Installing Alembic...
    pip install -q alembic
)
python -c "import pydantic" 2>nul
if errorlevel 1 (
    echo Installing Pydantic...
    pip install -q pydantic python-dotenv
)
echo ✓ Essential dependencies ready

echo [4/4] Starting services...
echo.
echo =======================================
echo  Starting Tru8 Backend Services  
echo =======================================
echo.
echo ✓ FastAPI will start on: http://localhost:8000
echo ✓ API docs available at: http://localhost:8000/api/docs
echo ✓ Celery worker will handle fact-checking tasks
echo.
echo Press Ctrl+C to stop all services
echo.

REM Start Celery worker in background (use python -m to ensure it's found)
echo Starting Celery worker...
start /b cmd /c "python -m celery -A app.workers worker --loglevel=info --logfile=celery.log 2>&1"

REM Wait a moment for worker to start
timeout /t 2 /nobreak >nul

REM Start FastAPI server (use python -m to ensure it's found)
echo Starting FastAPI server...
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000