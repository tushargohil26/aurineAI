@echo off
title AuraCode
cd /d "%~dp0"

:: === AUTO-UPDATE FROM GITHUB ===
if exist ".git" (
    echo   Checking for updates...
    git pull origin main --quiet 2>nul
    if errorlevel 1 (
        echo   Update check skipped (offline or no changes)
    ) else (
        echo   Code is up to date.
    )
)

:: === ENSURE .ENV EXISTS ===
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
    echo   Created .env config.
)

:: === ENSURE VENV + DEPS ===
if not exist ".venv\Scripts\python.exe" (
    echo   Setting up Python environment...
    python -m venv .venv 2>nul
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q 2>nul
    ".venv\Scripts\python.exe" auracode.py
) else (
    echo.
    echo   [X] Python 3.10+ required. Install from https://python.org
    pause
)
