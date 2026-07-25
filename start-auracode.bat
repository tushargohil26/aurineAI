@echo off
title AuraCode
cd /d "%~dp0"

:: === FAST STARTUP ===
if exist ".venv\.deps_installed" goto :ensure_dirs

:: === FIRST RUN SETUP ===
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
".venv\Scripts\python.exe" -m pip install rich questionary fastapi uvicorn pypdf openpyxl -q 2>nul
if not errorlevel 1 echo. > ".venv\.deps_installed"

:ensure_dirs
if not exist ".env" (
    if exist ".env.example" copy ".env.example" ".env" >nul
)
if not exist "%USERPROFILE%\.aurine-data" mkdir "%USERPROFILE%\.aurine-data" >nul
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul

:: === AUTO-UPDATE from GitHub ===
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import urllib.request,zipfile,os,shutil,tempfile;url='https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip';td=tempfile.mkdtemp();urllib.request.urlretrieve(url,os.path.join(td,'u.zip'));zipfile.ZipFile(os.path.join(td,'u.zip')).extractall(td);src=[d for d in os.listdir(td) if os.path.isdir(os.path.join(td,d)) and d.startswith('aurineAI')];[shutil.copy2(os.path.join(src[0],f),f) for f in ['auracode.py'] if os.path.exists(os.path.join(src[0],f))];[shutil.copytree(os.path.join(src[0],'app'),'app',dirs_exist_ok=True) if os.path.exists(os.path.join(src[0],'app')) else None];shutil.rmtree(td,ignore_errors=True)" 2>nul
)

:: === LAUNCH ===
echo.
echo   AuraCode v3.0 - AI Terminal Agent
echo   Local AI + Cloud Fallback ^| Ctrl+P: Palette ^| /help: Commands
echo.
".venv\Scripts\python.exe" auracode.py
