# AuraCode v2.0 - One-Line Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex

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

# STEP 1: Python
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
    Write-Host "  Installing Python..." -ForegroundColor Yellow
    try {
        winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;" + $env:Path
        $py = "python"
    } catch {
        Write-Host "  [X] Install Python 3.10+ from https://python.org then re-run" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  [OK] Python" -ForegroundColor Green

# STEP 2: Download
Write-Host "  [2/5] Downloading AuraCode..." -ForegroundColor Yellow
$zipUrl = "$RepoUrl/archive/refs/heads/main.zip"
$zipFile = "$env:TEMP\auracode_dl.zip"
$extractDir = "$env:TEMP\auracode_ext"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing -TimeoutSec 120
} catch {
    Write-Host "  [X] Download failed" -ForegroundColor Red
    exit 1
}

if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -Path $zipFile -DestinationPath $extractDir -Force
$srcDir = (Get-ChildItem $extractDir -Directory | Select-Object -First 1).FullName

# Stop running instances
Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# Clean install
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallDir\app" -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallDir\.auracode\sessions" -Force | Out-Null

# Copy files
Copy-Item "$srcDir\auracode.py" "$InstallDir\auracode.py" -Force
$pyFiles = Get-ChildItem "$srcDir\app\*.py" -ErrorAction SilentlyContinue
foreach ($f in $pyFiles) { Copy-Item $f.FullName "$InstallDir\app\$($f.Name)" -Force }
foreach ($f in @(".env.example", "requirements.txt")) {
    $s = Join-Path $srcDir $f
    if (Test-Path $s) { Copy-Item $s (Join-Path $InstallDir $f) -Force }
}

# Create .env
if (-not (Test-Path "$InstallDir\.env")) {
    @"
AI_PROVIDER=google
GOOGLE_API_KEY=
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

Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  [OK] Downloaded" -ForegroundColor Green

# STEP 3: Venv + ALL dependencies
Write-Host "  [3/5] Installing Python packages (this takes ~1 min)..." -ForegroundColor Yellow

$venvDir = "$InstallDir\.venv"
$venvPy = "$venvDir\Scripts\python.exe"
$venvPip = "$venvDir\Scripts\pip.exe"

if (-not (Test-Path "$venvDir\pyvenv.cfg")) {
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    if (Test-Path $venvDir) { Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue }
    & $py -m venv $venvDir
}

# Upgrade pip first
& $venvPy -m pip install --upgrade pip -q 2>$null

# Install ALL required packages - one by one to avoid failures
$packages = @("rich", "questionary", "openai", "httpx", "pydantic", "python-dotenv", "pygments", "tiktoken")
$failed = @()
foreach ($pkg in $packages) {
    Write-Host "  Installing $pkg..." -ForegroundColor DarkGray
    & $venvPy -m pip install $pkg -q 2>$null
    if ($LASTEXITCODE -ne 0) {
        # Retry without -q
        & $venvPy -m pip install $pkg 2>$null
    }
    # Verify
    $check = & $venvPy -c "import $($pkg.Replace('-','_').Split(' ')[0].ToLower())" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $failed += $pkg
        Write-Host "  [!] $pkg failed" -ForegroundColor Red
    } else {
        Write-Host "  [OK] $pkg" -ForegroundColor Green
    }
}

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "  Some packages failed: $($failed -join ', ')" -ForegroundColor Yellow
    Write-Host "  Retrying failed packages..." -ForegroundColor Yellow
    foreach ($pkg in $failed) {
        & $venvPy -m pip install $pkg --force-reinstall 2>$null
    }
}

Write-Host "  [OK] Packages installed" -ForegroundColor Green

# STEP 4: Create global command
Write-Host "  [4/5] Creating 'auracode' command..." -ForegroundColor Yellow

if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

@"
@echo off
title AuraCode v2.0
cd /d "$InstallDir"
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul
"$venvPy" auracode.py
if errorlevel 1 (
    echo.
    echo  AuraCode error. Make sure Python 3.10+ is installed.
    pause
)
"@ | Set-Content "$BinDir\auracode.bat" -NoNewline
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

$curPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$curPath;$BinDir", "User")
    $env:Path += ";$BinDir"
}
Write-Host "  [OK] Command ready" -ForegroundColor Green

# STEP 5: Verify
Write-Host "  [5/5] Verifying..." -ForegroundColor Yellow

$richCheck = & $venvPy -c "import rich; print(rich.__version__)" 2>&1
$qCheck = & $venvPy -c "import questionary; print(questionary.__version__)" 2>&1
$openaiCheck = & $venvPy -c "import openai; print(openai.__version__)" 2>&1

Write-Host "  rich: $richCheck" -ForegroundColor $(if ($richCheck -match "\d") { "Green" } else { "Red" })
Write-Host "  questionary: $qCheck" -ForegroundColor $(if ($qCheck -match "\d") { "Green" } else { "Red" })
Write-Host "  openai: $openaiCheck" -ForegroundColor $(if ($openaiCheck -match "\d") { "Green" } else { "Red" })

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    AuraCode v2.0 Installed!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Open a NEW terminal and type:" -ForegroundColor White
Write-Host ""
Write-Host "    auracode" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
Write-Host "  Features:" -ForegroundColor Cyan
Write-Host "    Ctrl+P     Command Palette" -ForegroundColor White
Write-Host "    /connect   Setup AI provider" -ForegroundColor White
Write-Host "    /agents    Switch agent" -ForegroundColor White
Write-Host "    /model     Switch model" -ForegroundColor White
Write-Host "    /session   Sessions" -ForegroundColor White
Write-Host "    /help      All commands" -ForegroundColor White
Write-Host ""
Write-Host "  Files: $InstallDir" -ForegroundColor DarkGray
Write-Host ""
