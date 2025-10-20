@echo off
REM Simple Auth Test - Just verify backend is responding
REM Usage: test-refactored-auth-simple.bat YOUR_JWT_TOKEN

setlocal

set TOKEN=%1

if "%TOKEN%"=="" (
    echo ERROR: No token provided
    echo.
    echo Usage: test-refactored-auth-simple.bat YOUR_TOKEN
    echo.
    echo To get a token:
    echo 1. Start backend: uvicorn app.main:app --reload
    echo 2. Login via frontend: http://localhost:3000
    echo 3. Open DevTools ^(F12^) -^> Application -^> Local Storage
    echo 4. Copy the Clerk token value
    exit /b 1
)

echo ==========================================
echo AUTH REFACTORING - QUICK TEST
echo ==========================================
echo.
echo Testing backend auth endpoints...
echo Token: %TOKEN:~0,20%...
echo.

REM Test /users/profile (most important endpoint)
echo [1/3] Testing GET /users/profile...
curl -s -X GET "http://localhost:8000/api/v1/users/profile" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" > test-result.json

REM Check if response contains expected fields
findstr /C:"email" test-result.json >nul
if %ERRORLEVEL%==0 (
    echo      [PASS] User profile endpoint working
    echo.
) else (
    echo      [FAIL] User profile endpoint failed
    type test-result.json
    echo.
    del test-result.json
    exit /b 1
)

REM Test /checks endpoint
echo [2/3] Testing GET /checks...
curl -s -X GET "http://localhost:8000/api/v1/checks?offset=0&limit=10" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" > test-result.json

findstr /C:"checks" test-result.json >nul
if %ERRORLEVEL%==0 (
    echo      [PASS] Checks endpoint working
    echo.
) else (
    echo      [FAIL] Checks endpoint failed
    type test-result.json
    echo.
    del test-result.json
    exit /b 1
)

REM Test /payments/subscription endpoint
echo [3/3] Testing GET /payments/subscription...
curl -s -X GET "http://localhost:8000/api/v1/payments/subscription" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" > test-result.json

findstr /C:"plan" test-result.json >nul
if %ERRORLEVEL%==0 (
    echo      [PASS] Subscription endpoint working
    echo.
) else (
    echo      [FAIL] Subscription endpoint failed
    type test-result.json
    echo.
    del test-result.json
    exit /b 1
)

del test-result.json

echo ==========================================
echo ALL QUICK TESTS PASSED!
echo ==========================================
echo.
echo Auth refactoring verified successfully.
echo All critical endpoints are working.
echo.
echo Next: Proceed with Week 1 Day 1 manual testing
echo.

exit /b 0
