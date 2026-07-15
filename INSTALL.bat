@echo off
title Aurine AI - Installer
color 0A
echo.
echo  ============================================
echo    AURINE AI - ONE CLICK INSTALL
echo  ============================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   Python not found. Installing...
    winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
)

echo.
echo [2/4] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    call .venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    call .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo.
echo [3/4] Setting up configuration...
if not exist ".env" (
    echo AI_PROVIDER=aurine> .env
)

echo.
echo [4/4] Creating desktop shortcut...
(
    echo @echo off
    echo title Aurine AI Assistant
    echo cd /d "%~dp0"
    echo start http://localhost:8000
    echo call .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
) > "%USERPROFILE%\Desktop\Aurine AI.bat"

echo.
echo  ============================================
echo    Install Complete!
echo  ============================================
echo.
echo  Double-click 'Aurine AI' on your Desktop to start
echo  Or run: START_AURINE.bat
echo.
echo  Open browser: http://localhost:8000
echo.

set /p start="Start Aurine now? (y/n): "
if /i "%start%"=="y" (
    start http://localhost:8000
    call .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
)
