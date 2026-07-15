@echo off
:: Aurine AI - Standalone launcher
:: Place this file anywhere in your PATH to run 'aurine' from any terminal
setlocal

:: Find Aurine directory
if defined AURINE_HOME (
    set "AURINE_DIR=%AURINE_HOME%"
) else if exist "%USERPROFILE%\.aurine\app" (
    set "AURINE_DIR=%USERPROFILE%\.aurine"
) else if exist "%~dp0app" (
    set "AURINE_DIR=%~dp0"
) else (
    echo Aurine not found. Install with: irm https://raw.githubusercontent.com/aurine/aurine-ai/main/install.ps1 ^| iex
    exit /b 1
)

cd /d "%AURINE_DIR%"

:: Ensure venv
if not exist ".venv\Scripts\python.exe" (
    echo Setting up Aurine...
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt >nul 2>&1
)

:: Run CLI
.\.venv\Scripts\python.exe -m app %*
