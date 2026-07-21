# AuraCode Setup - Run once on each device
# After this, 'auracode' works from ANY terminal, auto-updates, auto-detects AI

$ErrorActionPreference = "Stop"
$InstallDir = "$env:USERPROFILE\.auracode"
$ProjectDir = $PSScriptRoot

Write-Host ""
Write-Host "  AuraCode Setup" -ForegroundColor Cyan
Write-Host "  Device: $env:COMPUTERNAME ($env:OS)"
Write-Host ""

# === AUTO-UPDATE FROM GITHUB ===
if (Test-Path "$ProjectDir\.git") {
    Write-Host "  Checking for latest code..." -ForegroundColor DarkGray
    Push-Location $ProjectDir
    git pull origin main --quiet 2>$null
    Pop-Location
    Write-Host "  Code updated." -ForegroundColor Green
}

# === CREATE INSTALL DIR ===
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# === COPY LAUNCHERS ===
$files = @("auracode.bat", "auracode.ps1")
foreach ($f in $files) {
    $src = Join-Path $ProjectDir $f
    $dst = Join-Path $InstallDir $f
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "  [ok] $f" -ForegroundColor Green
    }
}

# === CREATE .ENV IF MISSING ===
$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    # Always create fresh .env - NEVER copy from source (may contain developer's personal keys)
    @"
AI_PROVIDER=aurine
OLLAMA_BASE_URL=http://127.0.0.1:11434
AURINE_NATIVE_MODEL=aurine-coder
AURINE_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OPENAI_CHAT_MODEL=gpt-4o-mini
GOOGLE_CHAT_MODEL=gemini-2.0-flash
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
VECTOR_DB=$ProjectDir\vector_store.sqlite3
DATA_DIR=$ProjectDir\data
"@ | Set-Content $envFile -NoNewline
    Write-Host "  [ok] Created fresh .env (Aurine works without API keys)" -ForegroundColor Green
}

# === ENSURE VENV + DEPS ===
Write-Host "  Checking dependencies..." -ForegroundColor DarkGray
Push-Location $ProjectDir
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv 2>$null
}
# Only install if marker file missing (fast startup)
if (-not (Test-Path ".venv\.deps_installed")) {
    Write-Host "  Installing packages (first run only)..." -ForegroundColor DarkGray
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt -q 2>$null
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path ".venv\.deps_installed" -Value "ok"
    }
}
Pop-Location
Write-Host "  [ok] Dependencies ready" -ForegroundColor Green

# === CREATE DEVICE DATA DIR ===
$dataDir = "$env:USERPROFILE\.aurine-data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Write-Host "  [ok] Device data: $dataDir" -ForegroundColor Green
}

# === CHECK AI BACKEND ===
$hasCloudKey = $false
$envContent = Get-Content $envFile -ErrorAction SilentlyContinue
if ($envContent) {
    foreach ($line in $envContent) {
        if ($line -match "^(GOOGLE_API_KEY|OPENAI_API_KEY|GROQ_API_KEY)=(.{10,})") {
            $hasCloudKey = $true
            $provider = $line.Split("=")[0]
            Write-Host "  [ok] $provider : configured" -ForegroundColor Green
        }
    }
}

$ollamaRunning = $false
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    $ollamaRunning = $true
    Write-Host "  [ok] Ollama: running locally" -ForegroundColor Green
} catch {}

if ($hasCloudKey -or $ollamaRunning) {
    Write-Host "  [ok] AI: ready (local or cloud)" -ForegroundColor Green
} else {
    Write-Host "  [!] Ollama not running" -ForegroundColor Yellow
    Write-Host "      Install Ollama: https://ollama.com" -ForegroundColor White
    Write-Host "      Aurine AI runs locally - no API key needed!" -ForegroundColor DarkGray
    Write-Host "      Or type 'auracode' then /connect for cloud providers" -ForegroundColor DarkGray
}

# === ADD TO PATH ===
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$InstallDir", "User")
    $env:Path += ";$InstallDir"
    Write-Host ""
    Write-Host "  [ok] Added to PATH" -ForegroundColor Green
} else {
    Write-Host "  [ok] Already in PATH" -ForegroundColor Green
}

# === CHECK TOOLS ===
Write-Host ""
Write-Host "  Tools:" -ForegroundColor Cyan
$tools = @("git", "python", "node", "docker", "code")
foreach ($tool in $tools) {
    $found = Get-Command $tool -ErrorAction SilentlyContinue
    if ($found) { Write-Host "    [ok] $tool" -ForegroundColor Green }
    else { Write-Host "    [-] $tool" -ForegroundColor DarkGray }
}

Write-Host ""
Write-Host "  Done! Type 'auracode' in any terminal to start." -ForegroundColor Cyan
Write-Host ""
Write-Host "  AuraCode v2.0 Features:" -ForegroundColor Cyan
Write-Host "    Ctrl+P     - Command Palette (fuzzy search all commands)" -ForegroundColor White
Write-Host "    /connect   - Connect AI provider (set API keys)" -ForegroundColor White
Write-Host "    /agents    - Switch AI agent" -ForegroundColor White
Write-Host "    /model     - Switch AI model" -ForegroundColor White
Write-Host "    /session   - Switch session" -ForegroundColor White
Write-Host "    /new       - New session" -ForegroundColor White
Write-Host "    /help      - Show all commands" -ForegroundColor White
Write-Host ""
Write-Host "  Auto-updates from GitHub on every launch." -ForegroundColor DarkGray
Write-Host "  Each device has its own data in: $dataDir" -ForegroundColor DarkGray
Write-Host ""
