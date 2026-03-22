@echo off
echo.
echo  =========================================
echo   Quota Tracker — AI Coding Tools
echo  =========================================
echo.

REM Check if .env exists
if not exist .env (
    echo  ERROR: .env file not found
    echo  Copy .env.example to .env and fill in your credentials
    pause
    exit /b 1
)

REM Install dependencies if needed
echo  Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo  Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo  Starting server at http://127.0.0.1:8000
echo  Press Ctrl+C to stop
echo.

REM Open browser after 2 seconds
start /b cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000"

REM Start FastAPI server
python app.py

pause
