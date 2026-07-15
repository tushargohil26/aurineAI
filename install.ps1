# ============================================
#  AURINE AI - ONE COMMAND INSTALL & RUN
#  Copy this entire line in PowerShell:
#  irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex
# ============================================

$ErrorActionPreference = "Continue"
$AurineDir = "$env:USERPROFILE\.aurine"
$GitHub = "https://github.com/tushargohil26/aurineAI.git"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    Aurine AI - Installing..." -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check/Install Python
Write-Host "[1/5] Checking Python..." -ForegroundColor White
$hasPython = $false
try {
    $pyVer = python --version 2>&1
    if ($pyVer -match "Python 3") {
        Write-Host "  Found: $pyVer" -ForegroundColor Green
        $hasPython = $true
    }
} catch { }

if (-not $hasPython) {
    Write-Host "  Python 3 not found. Installing..." -ForegroundColor Yellow
    try {
        winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements 2>$null
        $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
        Write-Host "  Python installed." -ForegroundColor Green
    } catch {
        Write-Host "  Cannot auto-install Python." -ForegroundColor Red
        Write-Host "  Download manually: https://python.org/downloads" -ForegroundColor Yellow
        Write-Host "  Check 'Add Python to PATH' during install." -ForegroundColor Yellow
        Write-Host ""
        pause
        exit 1
    }
}

# Step 2: Clone or update from GitHub
Write-Host "[2/5] Downloading Aurine AI..." -ForegroundColor White
if (Test-Path "$AurineDir\app\main.py") {
    Write-Host "  Updating existing install..." -ForegroundColor Green
    Push-Location $AurineDir
    git pull origin main --quiet 2>$null
    Pop-Location
} else {
    if (Test-Path $AurineDir) {
        Remove-Item -Path $AurineDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "  Cloning from GitHub..." -ForegroundColor Green
    $gitAvailable = Get-Command git -ErrorAction SilentlyContinue
    
    if ($gitAvailable) {
        git clone $GitHub $AurineDir --quiet 2>$null
    } else {
        Write-Host "  Git not found. Downloading ZIP..." -ForegroundColor Yellow
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $zipUrl = "https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip"
            $zipPath = "$env:TEMP\aurine-download.zip"
            $extractPath = "$env:TEMP\aurine-extract"
            
            Write-Host "  Downloading..." -ForegroundColor Green
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
            
            Write-Host "  Extracting..." -ForegroundColor Green
            if (Test-Path $extractPath) { Remove-Item $extractPath -Recurse -Force }
            Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
            
            $src = Get-ChildItem $extractPath | Where-Object { $_.PSIsContainer } | Select-Object -First 1
            Copy-Item -Path $src.FullName -Destination $AurineDir -Recurse -Force
            
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
            Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "  Download failed: $_" -ForegroundColor Red
            Write-Host "  Try installing Git: https://git-scm.com/download/win" -ForegroundColor Yellow
            pause
            exit 1
        }
    }
}

if (-not (Test-Path "$AurineDir\app\main.py")) {
    Write-Host "  ERROR: Download failed. Files not found." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "  Downloaded successfully." -ForegroundColor Green

# Step 3: Create virtual environment and install dependencies
Write-Host "[3/5] Installing dependencies..." -ForegroundColor White
Push-Location $AurineDir

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Green
    python -m venv .venv 2>$null
    .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet 2>$null
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    Write-Host "  Dependencies installed." -ForegroundColor Green
} else {
    Write-Host "  Virtual environment exists." -ForegroundColor Green
}

# Step 4: Configure
Write-Host "[4/5] Configuring..." -ForegroundColor White
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    } else {
        "AI_PROVIDER=aurine" | Out-File -FilePath ".env" -Encoding utf8
    }
    Write-Host "  Configuration created." -ForegroundColor Green
} else {
    Write-Host "  Configuration exists." -ForegroundColor Green
}

# Step 5: Create launcher
Write-Host "[5/5] Creating launcher..." -ForegroundColor White
$desktop = [Environment]::GetFolderPath("Desktop")
$launcher = @"
@echo off
title Aurine AI Assistant
cd /d "$AurineDir"
start http://localhost:8000
call .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
pause
"@
$launcher | Out-File -FilePath "$desktop\Aurine AI.bat" -Encoding ascii

Pop-Location

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    INSTALL COMPLETE!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location: $AurineDir" -ForegroundColor White
Write-Host "  Launcher: $desktop\Aurine AI.bat" -ForegroundColor White
Write-Host ""
Write-Host "  START AURINE:" -ForegroundColor Cyan
Write-Host "    Double-click 'Aurine AI' on Desktop" -ForegroundColor White
Write-Host "    Or run: cd $AurineDir; .\run.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  Open browser: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

# Ask to start now
$start = Read-Host "Start Aurine now? (Y/n)"
if ($start -ne "n" -and $start -ne "N") {
    Start-Process "http://localhost:8000"
    Push-Location $AurineDir
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
    Pop-Location
}
