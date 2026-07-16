# AuraCode v2.0 - One-Line Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex

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
        $v = & $c --version 2>&1 | Out-String
        if ($v -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) { $py = $c; break }
        }
    } catch {}
}
if (-not $py) {
    Write-Host "  Installing Python via winget..." -ForegroundColor Yellow
    try {
        Start-Process winget -ArgumentList "install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements" -Wait -NoNewWindow
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

Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallDir\app" -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallDir\.auracode\sessions" -Force | Out-Null

Copy-Item "$srcDir\auracode.py" "$InstallDir\auracode.py" -Force
$pyFiles = Get-ChildItem "$srcDir\app\*.py" -ErrorAction SilentlyContinue
foreach ($f in $pyFiles) { Copy-Item $f.FullName "$InstallDir\app\$($f.Name)" -Force }
foreach ($f in @(".env.example", "requirements.txt")) {
    $s = Join-Path $srcDir $f
    if (Test-Path $s) { Copy-Item $s (Join-Path $InstallDir $f) -Force }
}

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

# STEP 3: Venv + dependencies (uses cmd /c to avoid PowerShell stderr issues)
Write-Host "  [3/5] Installing Python packages..." -ForegroundColor Yellow

$venvDir = "$InstallDir\.venv"
$venvPy = "$venvDir\Scripts\python.exe"

if (-not (Test-Path "$venvDir\pyvenv.cfg")) {
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    if (Test-Path $venvDir) { Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue }
    cmd /c "`"$py`" -m venv `"$venvDir`"" 2>$null
}

# Upgrade pip
cmd /c "`"$venvPy`" -m pip install --upgrade pip 2>nul" 2>$null

# Install packages one by one using cmd /c (avoids PowerShell stderr errors)
$packages = @("rich", "questionary", "openai", "httpx", "pydantic", "python-dotenv", "pygments", "tiktoken")
$okCount = 0
$failCount = 0
foreach ($pkg in $packages) {
    cmd /c "`"$venvPy`" -m pip install $pkg 2>&1" | Out-Null
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-Host "  [OK] $pkg" -ForegroundColor Green
        $okCount++
    } else {
        Write-Host "  [!] $pkg - retrying..." -ForegroundColor Yellow
        cmd /c "`"$venvPy`" -m pip install $pkg --force-reinstall 2>&1" | Out-Null
        $check = cmd /c "`"$venvPy`" -c `"import $($pkg.Replace('-','_'))`" 2>&1"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] $pkg (retry)" -ForegroundColor Green
            $okCount++
        } else {
            Write-Host "  [X] $pkg FAILED" -ForegroundColor Red
            $failCount++
        }
    }
}

Write-Host "  Result: $okCount OK, $failCount failed" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })

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

$checks = @("rich", "questionary", "openai", "httpx", "pydantic", "dotenv")
foreach ($c in $checks) {
    $r = cmd /c "`"$venvPy`" -c `"import $c; print($c.__version__)`" 2>&1"
    if ($r -match "\d") {
        Write-Host "  [OK] $c : $r" -ForegroundColor Green
    } else {
        Write-Host "  [!!] $c : NOT INSTALLED" -ForegroundColor Red
    }
}

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
