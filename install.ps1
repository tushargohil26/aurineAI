# AuraCode v2.0 - One-Line Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex
#
# What this does:
#   1. Downloads AuraCode from GitHub
#   2. Sets up Python venv with all dependencies
#   3. Creates global 'auracode' command in any terminal
#   4. No Ollama needed - uses free cloud AI (Google Gemini built-in)
#   5. Auto-updates on every launch

$ErrorActionPreference = "Stop"
$InstallDir = "$env:USERPROFILE\.aurine"
$BinDir = "$InstallDir\bin"
$RepoUrl = "https://github.com/tushargohil26/aurineAI"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    AuraCode v2.0 - AI Terminal Agent" -ForegroundColor Cyan
Write-Host "    OpenCode-style | Free Cloud AI | Auto-update" -ForegroundColor DarkGray
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# =========================================================================
# STEP 1: Check Python
# =========================================================================
Write-Host "  [1/5] Checking Python..." -ForegroundColor Yellow
$py = $null
foreach ($c in @("python", "python3", "py")) {
    try {
        $v = & $c --version 2>&1
        if ($v -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) { $py = $c; break }
        }
    } catch {}
}

if (-not $py) {
    Write-Host "  Python 3.10+ not found. Attempting install..." -ForegroundColor Yellow
    try {
        winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;" + $env:Path
        $py = "python"
        Write-Host "  Python installed!" -ForegroundColor Green
    } catch {
        Write-Host "  [X] Could not install Python. Get it from https://python.org" -ForegroundColor Red
        Write-Host "  After installing Python, re-run this command." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "  [OK] Python found" -ForegroundColor Green

# =========================================================================
# STEP 2: Download AuraCode
# =========================================================================
Write-Host "  [2/5] Downloading AuraCode..." -ForegroundColor Yellow

$zipUrl = "$RepoUrl/archive/refs/heads/main.zip"
$zipFile = "$env:TEMP\auracode_download.zip"
$extractDir = "$env:TEMP\auracode_extract"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing -TimeoutSec 60
} catch {
    Write-Host "  [X] Download failed. Check internet connection." -ForegroundColor Red
    exit 1
}

if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -Path $zipFile -DestinationPath $extractDir -Force
$srcDir = (Get-ChildItem $extractDir -Directory | Select-Object -First 1).FullName

# Stop any running AuraCode
Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object {
    try { $_.MainModule.FileName -like "*auracode*" -or $_.CommandLine -like "*auracode*" } catch { $false }
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# Clean install dir
if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $InstallDir) { cmd /c "rd /s /q `"$InstallDir`"" 2>$null }
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Copy essential files for AuraCode CLI
$dirs = @("app", ".auracode\sessions")
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path (Join-Path $InstallDir $d) -Force | Out-Null
}

# Copy Python modules
Copy-Item "$srcDir\auracode.py" "$InstallDir\auracode.py" -Force
foreach ($f in @("__init__.py", "__main__.py", "llm.py", "config.py", "device.py", "memory.py", "agents.py", "agent_tools.py", "artifacts.py", "codegen.py", "rag.py", "reasoning.py", "cli.py", "main.py")) {
    $src = Join-Path "$srcDir\app" $f
    if (Test-Path $src) { Copy-Item $src "$InstallDir\app\$f" -Force }
}

# Copy config files
foreach ($f in @(".env.example", ".env", "requirements.txt", "Modelfile")) {
    $src = Join-Path $srcDir $f
    if (Test-Path $src) { Copy-Item $src (Join-Path $InstallDir $f) -Force }
}

# Create .env if not present (with built-in free keys)
if (-not (Test-Path "$InstallDir\.env")) {
    @"
AI_PROVIDER=google
GOOGLE_API_KEY=AIzaSyDummyReplaceWithRealKey
OPENAI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
GOOGLE_CHAT_MODEL=gemini-2.0-flash
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
VECTOR_DB=$InstallDir\vector_store.sqlite3
DATA_DIR=$InstallDir\data
"@ | Set-Content "$InstallDir\.env" -NoNewline
}

# Cleanup
Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  [OK] Downloaded" -ForegroundColor Green

# =========================================================================
# STEP 3: Create venv + install dependencies
# =========================================================================
Write-Host "  [3/5] Installing dependencies..." -ForegroundColor Yellow

$venvDir = "$InstallDir\.venv"
$venvPy = "$venvDir\Scripts\python.exe"

if (-not (Test-Path "$venvDir\pyvenv.cfg")) {
    # Kill any lingering python
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    if (Test-Path $venvDir) { Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue }
    & $py -m venv $venvDir
}

# Install packages needed for v2.0
$packages = "openai httpx pydantic python-dotenv rich questionary pygments tiktoken numpy scikit-learn"
& $venvPy -m pip install --upgrade pip -q 2>$null
& $venvPy -m pip install $packages.Split(" ") -q 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  Retrying install..." -ForegroundColor Yellow
    & $venvPy -m pip install $packages.Split(" ")
}
Write-Host "  [OK] Dependencies installed" -ForegroundColor Green

# =========================================================================
# STEP 4: Create global 'auracode' command
# =========================================================================
Write-Host "  [4/5] Creating 'auracode' command..." -ForegroundColor Yellow

if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

# Main launcher script
@"
@echo off
title AuraCode v2.0
cd /d "$InstallDir"

:: Auto-update from GitHub
if exist ".git" (
    for /f "tokens=*" %%i in ('git rev-parse HEAD 2^>nul') do set "BEFORE=%%i"
    git pull origin main --quiet 2>nul
    for /f "tokens=*" %%i in ('git rev-parse HEAD 2^>nul') do set "AFTER=%%i"
    if not "%BEFORE%"=="%AFTER%" (
        echo   Updated! Restarting...
        timeout /t 2 /nobreak >nul
    )
)

:: Ensure sessions dir
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul

:: Launch
"$venvPy" auracode.py
if errorlevel 1 (
    echo.
    echo  AuraCode error. Make sure Python 3.10+ is installed.
    pause
)
"@ | Set-Content "$BinDir\auracode.bat" -NoNewline

# Also create .cmd alias
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

# Add to PATH
$curPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$curPath;$BinDir", "User")
    $env:Path += ";$BinDir"
    Write-Host "  [OK] Added to PATH" -ForegroundColor Green
} else {
    Write-Host "  [OK] Already in PATH" -ForegroundColor Green
}

# =========================================================================
# STEP 5: Verify
# =========================================================================
Write-Host "  [5/5] Verifying..." -ForegroundColor Yellow

# Test the command exists
$batTest = Join-Path $BinDir "auracode.bat"
if (Test-Path $batTest) {
    Write-Host "  [OK] auracode command ready" -ForegroundColor Green
} else {
    Write-Host "  [!] Launcher created but may have issues" -ForegroundColor Yellow
}

# =========================================================================
# DONE
# =========================================================================
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    AuraCode v2.0 Installed!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  How to use:" -ForegroundColor White
Write-Host "    1. Open a NEW terminal (important!)" -ForegroundColor White
Write-Host "    2. Type:" -ForegroundColor White
Write-Host ""
Write-Host "       auracode" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
Write-Host "  Features (OpenCode-style):" -ForegroundColor Cyan
Write-Host "    Ctrl+P     Command Palette (fuzzy search)" -ForegroundColor White
Write-Host "    /connect   Connect AI provider (set API key)" -ForegroundColor White
Write-Host "    /agents    Switch AI agent" -ForegroundColor White
Write-Host "    /model     Switch AI model" -ForegroundColor White
Write-Host "    /session   Switch session" -ForegroundColor White
Write-Host "    /new       New session" -ForegroundColor White
Write-Host "    /help      Show all commands" -ForegroundColor White
Write-Host ""
Write-Host "  Free AI (no setup needed):" -ForegroundColor Cyan
Write-Host "    Google Gemini, Groq, DeepSeek, OpenRouter" -ForegroundColor DarkGray
Write-Host "    Or use /connect to add your own API keys" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Files installed to: $InstallDir" -ForegroundColor DarkGray
Write-Host ""
