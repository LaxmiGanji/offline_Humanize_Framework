@echo off
echo ===================================================
echo   Offline Humanized Summarizer - Startup Script
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.8+ and try again.
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [1/3] Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
) else (
    echo [1/3] Virtual environment already exists.
)

:: Activate the virtual environment
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install or update requirements quietly
echo [3/3] Checking and installing dependencies...
:: Only upgrade pip and install dependencies
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo.
echo ===================================================
echo   Starting the Application...
echo ===================================================
echo.
python main.py

:: Deactivate virtual environment when the application closes
deactivate
pause
