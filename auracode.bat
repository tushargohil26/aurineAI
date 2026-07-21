@echo off
title AuraCode
cd /d "%~dp0"

:: === ENSURE .ENV EXISTS ===
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
    echo   Created .env config.
)

:: === ENSURE VENV ===
if not exist ".venv\Scripts\python.exe" (
    echo   Setting up Python environment...
    python -m venv .venv 2>nul
)

:: === INSTALL DEPS ONLY IF NEEDED (fast startup) ===
if not exist ".venv\.deps_installed" (
    echo   Installing packages (first run only)...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q 2>nul
    if not errorlevel 1 echo. > ".venv\.deps_installed"
)

:: === ENSURE SESSIONS DIR ===
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul

:: === LAUNCH ===
".venv\Scripts\python.exe" auracode.py
