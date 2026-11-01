@echo off
title S9+ HDMI Viewer & Controller
echo ========================================================
echo   S9+ HDMI Viewer & Controller (SM-G965F)
echo ========================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: Check PySide6
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Installing required dependencies...
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install PySide6.
        pause
        exit /b 1
    )
)

echo Starting S9+ HDMI Viewer & Controller...
python "%~dp0main_hdmi_viewer.py"
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
