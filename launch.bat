@echo off
title Galaxy S9+ Recovery Console
echo ============================================
echo   Galaxy S9+ Recovery Console
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add to PATH" during installation.
    pause
    exit /b 1
)

:: Check PySide6
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo PySide6 not found. Installing dependencies...
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Starting application...
echo.
python "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
