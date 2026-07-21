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
AI_PROVIDER=google
GOOGLE_API_KEY=
GOOGLE_CHAT_MODEL=gemini-2.0-flash
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
GROQ_API_KEY=
DEEPSEEK_API_KEY=
VECTOR_DB=$ProjectDir\vector_store.sqlite3
DATA_DIR=$ProjectDir\data
"@ | Set-Content $envFile -NoNewline
    Write-Host "  [ok] Created fresh .env (add GOOGLE_API_KEY for free AI)" -ForegroundColor Green
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

if ($hasCloudKey) {
    Write-Host "  [ok] AI: ready (cloud)" -ForegroundColor Green
} else {
    Write-Host "  [!] No API key configured" -ForegroundColor Yellow
    Write-Host "      Get free key: https://aistudio.google.com/app/apikey" -ForegroundColor White
    Write-Host "      Add to .env: GOOGLE_API_KEY=your_key" -ForegroundColor DarkGray
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
Write-Host "  Features:" -ForegroundColor Cyan
Write-Host "    Ctrl+P     - Command Palette" -ForegroundColor White
Write-Host "    /connect   - Connect AI provider" -ForegroundColor White
Write-Host "    /agents    - Switch AI agent" -ForegroundColor White
Write-Host "    /session   - Switch session" -ForegroundColor White
Write-Host "    /help      - Show all commands" -ForegroundColor White
Write-Host ""
