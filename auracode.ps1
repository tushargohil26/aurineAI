$ErrorActionPreference = "Stop"

if (-not $env:AURACODE_TERMINAL_CHILD) {
  $scriptPath = $MyInvocation.MyCommand.Path
  $projectPath = Split-Path -Parent $scriptPath
  $command = "`$env:AURACODE_TERMINAL_CHILD='1'; Set-Location -LiteralPath '$projectPath'; & '$scriptPath'"
  Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $command)
  exit 0
}

$Host.UI.RawUI.WindowTitle = "AuraCode"
Clear-Host

# === AUTO-UPDATE FROM GITHUB ===
if (Test-Path ".git") {
    Write-Host "  Checking for updates..." -ForegroundColor DarkGray
    try {
        $before = (git rev-parse HEAD 2>$null).Trim()
        git pull origin main --quiet 2>$null
        $after = (git rev-parse HEAD 2>$null).Trim()
        if ($before -ne $after) {
            Write-Host "  Updated to latest version!" -ForegroundColor Green
            Write-Host "  Restarting..." -ForegroundColor DarkGray
            Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "`$env:AURACODE_TERMINAL_CHILD='1'; Set-Location '$PWD'; & '$PSCommandPath'")
            exit 0
        } else {
            Write-Host "  Up to date." -ForegroundColor Green
        }
    } catch {
        Write-Host "  Update check skipped." -ForegroundColor DarkGray
    }
}

# === ENSURE .ENV ===
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
    else { Set-Content ".env" "AI_PROVIDER=aurine`nGOOGLE_API_KEY=`nOPENAI_API_KEY=" }
    Write-Host "  Created .env config." -ForegroundColor Yellow
}

# === ENSURE VENV + DEPS ===
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "  Setting up Python environment..." -ForegroundColor DarkGray
    python -m venv .venv 2>$null
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q 2>$null

# === ENSURE DEVICE DATA DIR ===
$dataDir = "$env:USERPROFILE\.aurine-data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

Write-Host ""
Write-Host "  AuraCode v2.0 - OpenCode-style Terminal Agent" -ForegroundColor Cyan
Write-Host "  Ctrl+P: Command Palette  |  /connect: Setup AI  |  /help: All commands" -ForegroundColor DarkGray
Write-Host ""

# === LAUNCH ===
.\.venv\Scripts\python.exe auracode.py
