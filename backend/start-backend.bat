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
python -c "import redis; r = redis.Redis(host='localhost', port=6379, decode_responses=True); r.ping(); print('Redis is running')" 2>nul
if %errorlevel% == 0 (
    echo ✓ Redis is running
) else (
    echo ⚠ Redis not detected. Checking if Docker container exists...
    docker ps 2>nul | findstr redis >nul
    if %errorlevel% == 0 (
        echo ✓ Redis container found in Docker
    ) else (
        echo ⚠ Redis may not be running. If you have issues, ensure Redis is started:
        echo   Option 1: docker run -d -p 6379:6379 redis:alpine
        echo   Option 2: docker start redis ^(if container exists^)
        echo.
        echo Press any key to continue anyway...
        pause >nul
    )
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

REM Check and install ALL required dependencies systematically
echo [3/4] Checking and installing dependencies...
echo This may take a few moments on first run...

REM Core Web Framework
python -c "import fastapi" 2>nul || pip install -q fastapi
python -c "import uvicorn" 2>nul || pip install -q uvicorn
python -c "import multipart" 2>nul || pip install -q python-multipart
python -c "import pydantic_settings" 2>nul || pip install -q pydantic-settings
python -c "import aiofiles" 2>nul || pip install -q aiofiles

REM Database
python -c "import sqlmodel" 2>nul || pip install -q sqlmodel
python -c "import asyncpg" 2>nul || pip install -q asyncpg
python -c "import alembic" 2>nul || pip install -q alembic

REM Task Queue & Cache
python -c "import celery" 2>nul || pip install -q celery
python -c "import redis" 2>nul || pip install -q redis

REM Authentication
python -c "import jwt" 2>nul || pip install -q pyjwt
python -c "import httpx" 2>nul || pip install -q httpx
python -c "import cryptography" 2>nul || pip install -q cryptography

REM Payments
python -c "import stripe" 2>nul || pip install -q stripe

REM Push Notifications
python -c "import exponent_server_sdk" 2>nul || pip install -q exponent-server-sdk

REM Content Processing
python -c "import bleach" 2>nul || pip install -q bleach
python -c "import trafilatura" 2>nul || pip install -q trafilatura
python -c "import readability" 2>nul || pip install -q readability-lxml
python -c "import pytesseract" 2>nul || pip install -q pytesseract
python -c "import youtube_transcript_api" 2>nul || pip install -q youtube-transcript-api
python -c "import PIL" 2>nul || pip install -q Pillow

REM Vector Search
python -c "import qdrant_client" 2>nul || pip install -q qdrant-client

REM Monitoring
python -c "import sentry_sdk" 2>nul || pip install -q sentry-sdk
python -c "import prometheus_client" 2>nul || pip install -q prometheus-client

REM Note: Skipping ML libraries (sentence-transformers, torch, transformers, scikit-learn)
REM due to Python 3.13 compatibility issues. Install manually if needed:
REM pip install sentence-transformers torch transformers scikit-learn

echo ✓ Essential dependencies installed

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
REM Write logs to backend directory so we can see errors immediately
set CELERY_LOG=celery-worker.log
REM CRITICAL: Use solo pool for Windows compatibility AND correct module path
start "Tru8 Celery Worker" cmd /c "python -m celery -A app.workers.celery_app worker --pool=solo --loglevel=info --logfile=%CELERY_LOG% 2>&1"
echo Celery logs: %CELERY_LOG%
echo [Memory Safe] Using solo pool for Windows compatibility

REM Wait a moment for worker to start
timeout /t 2 /nobreak >nul

REM Start FastAPI server (use python -m to ensure it's found)
REM Use --reload-dir to limit file watching scope
echo Starting FastAPI server...
python -m uvicorn main:app --reload --reload-dir app --host 127.0.0.1 --port 8000