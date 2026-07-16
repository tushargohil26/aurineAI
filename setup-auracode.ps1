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
    $envExample = Join-Path $ProjectDir ".env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "  [ok] Created .env" -ForegroundColor Green
    } else {
        Set-Content -Path $envFile -Value "AI_PROVIDER=aurine`nGOOGLE_API_KEY=`nOPENAI_API_KEY="
    }
}

# === ENSURE VENV + DEPS ===
Write-Host "  Installing dependencies..." -ForegroundColor DarkGray
Push-Location $ProjectDir
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv 2>$null
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q 2>$null
Pop-Location
Write-Host "  [ok] Dependencies installed" -ForegroundColor Green

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
    Write-Host "  [ok] AI: ready (cloud or local)" -ForegroundColor Green
} else {
    Write-Host "  [!] AI: no backend found" -ForegroundColor Yellow
    Write-Host "      AuraCode will use built-in defaults." -ForegroundColor DarkGray
    Write-Host "      For best results, add GOOGLE_API_KEY to .env" -ForegroundColor DarkGray
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
