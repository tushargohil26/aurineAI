$ErrorActionPreference = "Stop"

# Ensure .env
if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
  Write-Host "Created .env from .env.example."
}

# Ensure venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
  python -m venv .venv
  Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Check deps
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Checking Python dependencies..." -ForegroundColor Cyan
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Check provider
$envText = Get-Content ".env" -Raw
if ($envText -match "AI_PROVIDER\s*=\s*ollama") {
  if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama is not installed or not in PATH." -ForegroundColor Yellow
    Write-Host "Install: irm https://ollama.com/install.ps1 | iex"
    Write-Host "Then run: .\setup-ollama.ps1"
    exit 1
  }
}

Write-Host ""
# Kill old server on port 8000
try {
  $listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  foreach ($listener in $listeners) {
    $processId = $listener.OwningProcess
    if ($processId -and $processId -ne $PID) {
      Write-Host "Stopping old server on port 8000 (PID $processId)..." -ForegroundColor Yellow
      Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
  }
} catch {}

Write-Host "Starting Aurine at http://localhost:8000" -ForegroundColor Green
Write-Host "Keep this terminal open while using the app." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
