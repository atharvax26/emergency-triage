@echo off
echo ========================================
echo Emergency Triage Assistant - Dev Server
echo ========================================
echo.

cd /d "%~dp0"

echo Checking for node_modules...
if not exist "node_modules\" (
    echo Installing dependencies...
    call npm install
    echo.
)

echo Starting development server...
echo.
echo The app will be available at: http://localhost:8080
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

echo Opening Chrome...
timeout /t 3 /nobreak >nul
start chrome http://localhost:8080

call npm run dev
