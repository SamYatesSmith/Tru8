@echo off
REM Consistency Test Runner for Tru8
REM This script runs 5 consistency tests with diagnostic logging

echo ========================================
echo TRU8 CONSISTENCY TEST
echo ========================================
echo.
echo This will run 5 fact-checks on the same article
echo to test for consistency issues.
echo.
echo Backend logs will show diagnostic info with emoji markers:
echo   - 🔎 QUERY RESULT  = Generated search queries
echo   - 🔍 SEARCH RESULTS = Results from providers
echo   - ⏱️ TIMEOUT = Provider timeouts
echo   - ❌ ERROR = Failures
echo.
echo BEFORE RUNNING:
echo 1. Start backend in separate terminal:
echo    cd backend
echo    uvicorn main:app --reload
echo.
echo 2. Make sure ENABLE_QUERY_EXPANSION=true in .env
echo.
pause

echo.
echo Starting test...
python test_consistency.py --runs 5 --wait 60

echo.
echo ========================================
echo TEST COMPLETE
echo ========================================
echo.
echo Results saved to: consistency_test_logs/
echo.
echo Next: Check the backend console logs for diagnostic output
echo Look for patterns in query generation and search results.
echo.
pause
