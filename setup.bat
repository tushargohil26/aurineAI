@echo off
title Aurine AI Assistant - Setup
color 0A
echo.
echo  ============================================
echo    Aurine AI Assistant - One-Command Setup
echo  ============================================
echo.

cd /d "%~dp0"

echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo   Found: %PYVER%

echo.
echo [2/5] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    echo   Virtual environment created.
) else (
    echo   Virtual environment already exists.
)

echo.
echo [3/5] Installing dependencies...
call .venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
call .venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo [4/5] Setting up configuration...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo   Created .env from .env.example
    ) else (
        echo AI_PROVIDER=aurine> .env
        echo Created default .env
    )
) else (
    echo   .env already exists.
)

echo.
echo [5/5] Checking Ollama (for local AI)...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo   Ollama found. Starting model pull...
    call ollama pull qwen2.5-coder:7b >nul 2>&1
    call ollama pull nomic-embed-text >nul 2>&1
    echo   Models ready.
) else (
    echo   Ollama not found. You can:
    echo     1. Install Ollama: https://ollama.com/download
    echo     2. Or use a cloud API key (Groq, OpenAI, Google, etc.)
    echo     Set AI_PROVIDER and API key in .env file.
)

echo.
echo  ============================================
echo    Setup Complete!
echo  ============================================
echo.
echo  To start Aurine:
echo    Double-click START_AURINE.bat
echo    Or run: run.ps1
echo.
echo  Open browser: http://localhost:8000
echo.
pause
