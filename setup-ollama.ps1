$ErrorActionPreference = "Stop"

Write-Host "Checking Ollama..." -ForegroundColor Cyan

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
  Write-Host ""
  Write-Host "Ollama is not installed or not in PATH." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "Install it with this official PowerShell command:" -ForegroundColor White
  Write-Host "irm https://ollama.com/install.ps1 | iex" -ForegroundColor Green
  Write-Host ""
  Write-Host "After install:"
  Write-Host "1. Close this PowerShell window."
  Write-Host "2. Open a new PowerShell window."
  Write-Host "3. Run: ollama --version"
  Write-Host "4. Then run this script again: .\setup-ollama.ps1"
  exit 1
}

Write-Host "Ollama found: $($ollama.Source)" -ForegroundColor Green

try {
  Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing | Out-Null
  Write-Host "Ollama server is running." -ForegroundColor Green
} catch {
  Write-Host "Starting Ollama..." -ForegroundColor Yellow
  Start-Process -FilePath "ollama" -ArgumentList @("serve") -WindowStyle Hidden
  Start-Sleep -Seconds 3
}

Write-Host "Pulling coding model..." -ForegroundColor Cyan
ollama pull qwen2.5-coder:7b

Write-Host "Pulling embedding model..." -ForegroundColor Cyan
ollama pull nomic-embed-text

Write-Host ""
Write-Host "Ollama setup complete." -ForegroundColor Green
Write-Host "Now run: .\run.ps1"
