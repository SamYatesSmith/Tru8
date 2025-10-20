@echo off
REM Simple Check Creation Test
REM Usage: test-check-creation.bat YOUR_JWT_TOKEN

setlocal

set TOKEN=%1

if "%TOKEN%"=="" (
    echo ERROR: No token provided
    echo Usage: test-check-creation.bat YOUR_TOKEN
    exit /b 1
)

echo ==========================================
echo CHECK CREATION - DIAGNOSTIC TEST
echo ==========================================
echo.
echo Token: %TOKEN:~0,20%...
echo.

REM Test 1: Verify auth still works
echo [1/3] Testing auth (GET /users/profile)...
curl -s -w "\nHTTP Status: %%{http_code}\n" -X GET "http://localhost:8000/api/v1/users/profile" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" --max-time 5

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Auth test failed or timed out
    exit /b 1
)
echo.

REM Test 2: Try GET /checks (should work based on logs)
echo [2/3] Testing GET /checks...
curl -s -w "\nHTTP Status: %%{http_code}\n" -X GET "http://localhost:8000/api/v1/checks?offset=0&limit=5" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" --max-time 5

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] GET /checks failed or timed out
    exit /b 1
)
echo.

REM Test 3: Try POST /checks with minimal payload
echo [3/3] Testing POST /checks (creating fact-check)...
echo Payload: {"input_type": "text", "content": "Test claim"}
echo.

curl -v -X POST "http://localhost:8000/api/v1/checks" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{\"input_type\": \"text\", \"content\": \"The Eiffel Tower was completed in 1889.\"}" ^
  --max-time 10

echo.
echo.
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] POST /checks timed out or failed
    echo Check backend logs for errors
    exit /b 1
) else (
    echo [SUCCESS] POST /checks completed
)

echo.
echo ==========================================
echo TEST COMPLETE
echo ==========================================
