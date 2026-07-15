# ============================================
#  AURINE AI - ONE COMMAND INSTALL & RUN
#  Copy this entire script and paste in PowerShell
# ============================================

$ErrorActionPreference = "Stop"
$AurineDir = "$env:USERPROFILE\.aurine"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    Aurine AI - Installing..." -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyVer = python --version 2>&1
    Write-Host "  Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  Python not found. Installing..." -ForegroundColor Yellow
    try {
        winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    } catch {
        Write-Host "  Cannot auto-install Python." -ForegroundColor Red
        Write-Host "  Download manually: https://python.org" -ForegroundColor Yellow
        Write-Host "  Check 'Add Python to PATH' during install." -ForegroundColor Yellow
        exit 1
    }
    $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
}

# Find source - check multiple locations
$sourceDir = $null
$searchPaths = @(
    "C:\Users\ADMIN\Documents\Codex\2026-07-01\abhi-bhi-chat-sub-niche-ho-2\work\aurine-src\aurine-ai-assistant\aurine-ai-assistant",
    "$env:USERPROFILE\aurine-ai-assistant",
    "$env:USERPROFILE\Documents\aurine-ai-assistant",
    "."
)

foreach ($path in $searchPaths) {
    if (Test-Path "$path\app\main.py") {
        $sourceDir = $path
        break
    }
}

if (-not $sourceDir) {
    Write-Host "  Source not found. Creating fresh install..." -ForegroundColor Yellow
    $sourceDir = $AurineDir
    New-Item -ItemType Directory -Path $AurineDir -Force | Out-Null
    
    # Create minimal Aurine
    Write-Host "  Creating Aurine workspace..." -ForegroundColor Green
    
    $mainPy = @"
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
"@
    New-Item -ItemType Directory -Path "$AurineDir\app" -Force | Out-Null
    New-Item -ItemType Directory -Path "$AurineDir\static" -Force | Out-Null
    $mainPy | Out-File -FilePath "$AurineDir\app\main.py" -Encoding utf8
    
    "# Aurine AI" | Out-File -FilePath "$AurineDir\app\__init__.py" -Encoding utf8
    "AI_PROVIDER=aurine" | Out-File -FilePath "$AurineDir\.env" -Encoding utf8
    "fastapi>=0.115.0`nuvicorn[standard]>=0.34.0`npython-multipart>=0.0.20" | Out-File -FilePath "$AurineDir\requirements.txt" -Encoding utf8
}

# Copy source to .aurine if different
if ($sourceDir -ne $AurineDir) {
    if (-not (Test-Path "$AurineDir\app\main.py")) {
        Write-Host "  Copying Aurine files..." -ForegroundColor Green
        Copy-Item -Path $sourceDir -Destination $AurineDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Push-Location $AurineDir

# Create venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Green
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip >$null 2>&1
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Setup env
if (-not (Test-Path ".env")) {
    "AI_PROVIDER=aurine" | Out-File -FilePath ".env" -Encoding utf8
}

# Check Ollama
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    Write-Host "  Setting up AI models..." -ForegroundColor Green
    ollama pull qwen2.5-coder:7b 2>$null
    ollama pull nomic-embed-text 2>$null
}

Pop-Location

# Create desktop shortcut
$desktop = [Environment]::GetFolderPath("Desktop")
$batContent = @"
@echo off
title Aurine AI Assistant
cd /d "$AurineDir"
start http://localhost:8000
call .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
"@
$batContent | Out-File -FilePath "$desktop\Aurine AI.bat" -Encoding ascii

# Create start menu shortcut
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$batContent | Out-File -FilePath "$startMenu\Aurine AI.bat" -Encoding ascii

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Install Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Location: $AurineDir" -ForegroundColor White
Write-Host ""
Write-Host "  START AURINE:" -ForegroundColor Cyan
Write-Host "    Double-click 'Aurine AI' on Desktop" -ForegroundColor White
Write-Host "    Or run: cd $AurineDir; .\run.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  Open browser: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

# Auto-start
$start = Read-Host "Start Aurine now? (y/n)"
if ($start -eq "y" -or $start -eq "Y" -or $start -eq "") {
    Start-Process "http://localhost:8000"
    Push-Location $AurineDir
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
    Pop-Location
}
