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
Write-Host ""
Write-Host "  AuraCode" -ForegroundColor Cyan
Write-Host "  v1.0" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
  else { Set-Content ".env" "AI_PROVIDER=aurine`n" }
  Write-Host "  Created .env config." -ForegroundColor Yellow
}

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q 2>$null
.\.venv\Scripts\python.exe auracode.py
