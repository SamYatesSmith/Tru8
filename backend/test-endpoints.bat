@echo off
echo Testing API endpoints...
echo.

echo 1. Testing health endpoint...
curl http://localhost:8000/api/v1/health
echo.
echo.

echo 2. Testing root endpoint...
curl http://localhost:8000/
echo.
echo.

echo 3. Checking if backend is running on port 8000...
netstat -an | findstr "8000"
echo.
echo.

echo Done!
pause
