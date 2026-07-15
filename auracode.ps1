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
Write-Host "    ___                     ______          __     " -ForegroundColor Cyan
Write-Host "   /   |  __  __________ _ / ____/___  ____/ /__   " -ForegroundColor Cyan
Write-Host "  / /| | / / / / ___/ __ ``/ /   / __ \/ __  / _ \  " -ForegroundColor Cyan
Write-Host " / ___ |/ /_/ / /  / /_/ / /___/ /_/ / /_/ /  __/  " -ForegroundColor Cyan
Write-Host "/_/  |_|\__,_/_/   \__,_/\____/\____/\__,_/\___/   " -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env. Edit it if needed, then run again."
  exit 1
}

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe auracode.py
