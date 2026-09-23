@echo off
title Twin-Mate
cd /d "%~dp0"

echo Stopping old server on port 5000 (if any)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
)
call venv\Scripts\activate.bat

pip install -r requirements.txt -q

echo.
echo Open: http://127.0.0.1:5000
echo.
python app.py
