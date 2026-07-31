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

# === FAST STARTUP CHECK ===
$venvPy = ".\.venv\Scripts\python.exe"
$depsOk = Test-Path ".\.venv\.deps_installed"

if (-not $depsOk) {
    Write-Host "  Setting up..." -ForegroundColor DarkGray
    if (-not (Test-Path $venvPy)) {
        python -m venv .venv 2>$null
    }
    if (Test-Path $venvPy) {
        & $venvPy -m pip install rich questionary fastapi uvicorn pypdf openpyxl -q 2>$null
        if ($LASTEXITCODE -eq 0) {
            Set-Content -Path ".\.venv\.deps_installed" -Value "ok" -Force
            $depsOk = $true
        }
    }
}

if (-not (Test-Path $venvPy)) {
    Write-Host "  [X] Python 3.10+ required. Install from https://python.org" -ForegroundColor Red
    pause
    exit 1
}

# === ENSURE .ENV ===
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" }
    else {
        @"
AI_PROVIDER=aurine
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
AURINE_NATIVE_MODEL=qwen2.5-coder:7b
AURINE_EMBEDDING_MODEL=nomic-embed-text
GOOGLE_API_KEY=
GOOGLE_CHAT_MODEL=gemini-2.0-flash
GROQ_API_KEY=
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
VECTOR_DB=$PWD\vector_store.sqlite3
DATA_DIR=$PWD\data
"@ | Set-Content ".env" -NoNewline
    }
    Write-Host "  Created .env config." -ForegroundColor Yellow
}

# === ENSURE DEVICE DATA DIR ===
$dataDir = "$env:USERPROFILE\.aurine-data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

# === ENSURE SESSIONS DIR ===
if (-not (Test-Path ".auracode\sessions")) {
    New-Item -ItemType Directory -Path ".auracode\sessions" -Force | Out-Null
}

Write-Host ""
Write-Host "  AuraCode v3.0 - AI Terminal Agent" -ForegroundColor Cyan
Write-Host "  Local AI + Cloud Fallback | Ctrl+P: Palette | /help: Commands" -ForegroundColor DarkGray
Write-Host ""

# === LAUNCH ===
& $venvPy auracode.py
