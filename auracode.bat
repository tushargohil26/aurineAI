@echo off
title AuraCode
cd /d "%~dp0"

:: === FAST STARTUP: skip if deps already installed ===
if exist ".venv\.deps_installed" goto :ensure_env

:: === FIRST RUN: setup ===
if not exist ".venv\Scripts\python.exe" (
    echo   Setting up Python environment...
    python -m venv .venv 2>nul
)
if not exist ".venv\Scripts\python.exe" (
    echo   [X] Python 3.10+ required. Install from python.org
    pause
    exit /b 1
)
echo   Installing packages (first run only)...
".venv\Scripts\python.exe" -m pip install rich questionary fastapi uvicorn pypdf openpyxl python-multipart -q
".venv\Scripts\python.exe" -c "import rich, questionary, fastapi, uvicorn, pypdf, openpyxl, python_multipart" >nul 2>nul && echo ok> ".venv\.deps_installed"

:ensure_env
:: === ENSURE .ENV ===
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
    echo   Created .env config.
)

:: === ENSURE SESSIONS DIR ===
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul

:: === LAUNCH ===
".venv\Scripts\python.exe" auracode.py
