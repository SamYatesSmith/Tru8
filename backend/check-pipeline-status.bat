@echo off
REM Check pipeline status for a specific check
REM Usage: check-pipeline-status.bat CHECK_ID YOUR_JWT_TOKEN

setlocal

set CHECK_ID=%1
set TOKEN=%2

if "%CHECK_ID%"=="" (
    echo ERROR: No check ID provided
    echo Usage: check-pipeline-status.bat CHECK_ID YOUR_TOKEN
    exit /b 1
)

if "%TOKEN%"=="" (
    echo ERROR: No token provided
    echo Usage: check-pipeline-status.bat CHECK_ID YOUR_TOKEN
    exit /b 1
)

echo ==========================================
echo CHECKING PIPELINE STATUS
echo ==========================================
echo Check ID: %CHECK_ID%
echo.

curl -s -X GET "http://localhost:8000/api/v1/checks/%CHECK_ID%" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"

echo.
echo.
echo ==========================================
