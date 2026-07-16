@echo off
title AuraCode
cd /d "%~dp0"

:: === AUTO-UPDATE FROM GITHUB ===
if exist ".git" (
    echo   Checking for updates...
    git pull origin main --quiet 2>nul
)

:: === ENSURE .ENV ===
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)

:: === ENSURE VENV + DEPS ===
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv 2>nul
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q 2>nul

:: === ENSURE DEVICE DATA DIR ===
if not exist "%USERPROFILE%\.aurine-data" mkdir "%USERPROFILE%\.aurine-data" >nul

:: === ENSURE SESSIONS DIR ===
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul

:: === LAUNCH ===
echo.
echo   AuraCode v2.0 - OpenCode-style Terminal Agent
echo   Ctrl+P: Command Palette  /connect: Setup AI  /help: All commands
echo.
".venv\Scripts\python.exe" auracode.py
