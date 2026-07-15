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

# Copy source to .aurine
if (-not (Test-Path "$AurineDir\app\main.py")) {
    if ($sourceDir -and (Test-Path "$sourceDir\app\main.py")) {
        Write-Host "  Copying Aurine files..." -ForegroundColor Green
        Copy-Item -Path $sourceDir -Destination $AurineDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  Source not found. Cloning from GitHub..." -ForegroundColor Yellow
        try {
            git clone https://github.com/tushargohil26/aurineAI.git $AurineDir 2>$null
        } catch {
            Write-Host "  Git not available. Downloading..." -ForegroundColor Yellow
            $zipUrl = "https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip"
            $zipPath = "$env:TEMP\aurine.zip"
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
                Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\aurine-extract" -Force
                $src = Get-ChildItem "$env:TEMP\aurine-extract" | Select-Object -First 1
                Copy-Item -Path $src.FullName -Destination $AurineDir -Recurse -Force
                Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
                Remove-Item "$env:TEMP\aurine-extract" -Recurse -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Host "  Download failed. Please install Git first." -ForegroundColor Red
            }
        }
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
try {
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollama) {
        Write-Host "  Ollama found. Pulling models (may take a few minutes)..." -ForegroundColor Green
        $proc1 = Start-Process ollama -ArgumentList "pull qwen2.5-coder:7b" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
        $proc2 = Start-Process ollama -ArgumentList "pull nomic-embed-text" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
        Write-Host "  Done." -ForegroundColor Green
    } else {
        Write-Host "  Ollama not installed. Using cloud AI instead." -ForegroundColor Yellow
        Write-Host "  Set an API key in .env (OPENAI_API_KEY, GROQ_API_KEY, etc.)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Ollama setup skipped. You can configure AI provider later in .env" -ForegroundColor Yellow
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
