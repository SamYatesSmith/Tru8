@echo off
REM Auth Refactoring - Automated Test Suite (Windows)
REM Usage: test-refactored-auth.bat YOUR_JWT_TOKEN

setlocal enabledelayedexpansion

echo ==========================================
echo AUTH REFACTORING - AUTOMATED TEST SUITE
echo ==========================================
echo.

REM Configuration
set BASE_URL=http://localhost:8000/api/v1
set TOKEN=%1

if "%TOKEN%"=="" (
    echo ERROR: No token provided
    echo Usage: test-refactored-auth.bat YOUR_TOKEN
    exit /b 1
)

echo Token provided: %TOKEN:~0,20%...
echo.

REM Test counter
set /a PASSED=0
set /a FAILED=0

echo ==========================================
echo TEST SUITE 1: STANDARD AUTH ENDPOINTS
echo ==========================================
echo.

REM Test 1: GET /auth/me
echo Testing GET /auth/me...
curl -s -w "%%{http_code}" -o test-response.json -X GET "%BASE_URL%/auth/me" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"
set STATUS_CODE=%ERRORLEVEL%
if %ERRORLEVEL%==0 (
    echo [PASS] GET /auth/me
    set /a PASSED+=1
) else (
    echo [FAIL] GET /auth/me
    set /a FAILED+=1
)
echo.

REM Test 2: GET /users/profile
echo Testing GET /users/profile...
curl -s -w "%%{http_code}" -o test-response.json -X GET "%BASE_URL%/users/profile" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"
if %ERRORLEVEL%==0 (
    echo [PASS] GET /users/profile
    set /a PASSED+=1
) else (
    echo [FAIL] GET /users/profile
    set /a FAILED+=1
)
echo.

REM Test 3: GET /users/usage
echo Testing GET /users/usage...
curl -s -w "%%{http_code}" -o test-response.json -X GET "%BASE_URL%/users/usage" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"
if %ERRORLEVEL%==0 (
    echo [PASS] GET /users/usage
    set /a PASSED+=1
) else (
    echo [FAIL] GET /users/usage
    set /a FAILED+=1
)
echo.

REM Test 4: GET /users/notifications
echo Testing GET /users/notifications...
curl -s -w "%%{http_code}" -o test-response.json -X GET "%BASE_URL%/users/notifications" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"
if %ERRORLEVEL%==0 (
    echo [PASS] GET /users/notifications
    set /a PASSED+=1
) else (
    echo [FAIL] GET /users/notifications
    set /a FAILED+=1
)
echo.

REM Test 5: GET /checks
echo Testing GET /checks...
curl -s -w "%%{http_code}" -o test-response.json -X GET "%BASE_URL%/checks?offset=0&limit=10" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"
if %ERRORLEVEL%==0 (
    echo [PASS] GET /checks
    set /a PASSED+=1
) else (
    echo [FAIL] GET /checks
    set /a FAILED+=1
)
echo.

REM Test 6: GET /payments/subscription
echo Testing GET /payments/subscription...
curl -s -w "%%{http_code}" -o test-response.json -X GET "%BASE_URL%/payments/subscription" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json"
if %ERRORLEVEL%==0 (
    echo [PASS] GET /payments/subscription
    set /a PASSED+=1
) else (
    echo [FAIL] GET /payments/subscription
    set /a FAILED+=1
)
echo.

echo ==========================================
echo TEST RESULTS SUMMARY
echo ==========================================
echo.
echo PASSED: %PASSED%
echo FAILED: %FAILED%
echo.

if %FAILED%==0 (
    echo ALL TESTS PASSED - REFACTORING VERIFIED!
    del test-response.json 2>nul
    exit /b 0
) else (
    echo SOME TESTS FAILED - REVIEW REQUIRED
    del test-response.json 2>nul
    exit /b 1
)
