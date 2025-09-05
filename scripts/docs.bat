@echo off
REM Quick MkDocs helper script for Windows

echo 🚀 Memori SDK - Documentation Helper
echo ======================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is required but not installed.
    echo Please install Python from https://python.org/
    pause
    exit /b 1
)

REM Get the script directory
set SCRIPT_DIR=%~dp0

REM Run the Python script with all arguments
python "%SCRIPT_DIR%docs_dev.py" %*