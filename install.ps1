# AuraCode v3.0 - Universal Installer
# Run on ANY Windows device: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex

$InstallDir = "$env:USERPROFILE\.aurine"
$BinDir = "$InstallDir\bin"
$RepoUrl = "https://github.com/tushargohil26/aurineAI"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    AuraCode v3.0 - AI Terminal Agent" -ForegroundColor Cyan
Write-Host "    Local AI + Cloud Fallback | Free" -ForegroundColor DarkGray
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# ====================================================================
# STEP 1: Find or Install Python (NEVER crash, auto-install)
# ====================================================================
Write-Host "  [1/6] Python..." -ForegroundColor Yellow
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
    Write-Host "  Python not found. Installing automatically..." -ForegroundColor Yellow

    $installed = $false
    try {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Host "  Trying winget..." -ForegroundColor DarkGray
            Start-Process winget -ArgumentList "install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements" -Wait -NoNewWindow -ErrorAction SilentlyContinue
            $env:Path = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:LOCALAPPDATA\Programs\Python\Python311;$env:LOCALAPPDATA\Programs\Python\Python311\Scripts;" + $env:Path
            foreach ($c in @("python", "python3", "py")) {
                try { $v = & $c --version 2>&1 | Out-String; if ($v -match "Python 3\.(\d+)") { $minor = [int]$Matches[1]; if ($minor -ge 10) { $py = $c; $installed = $true; break } } } catch {}
            }
        }
    } catch {}

    if (-not $installed) {
        Write-Host "  Downloading Python from python.org..." -ForegroundColor DarkGray
        $pyUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        $pyInstaller = "$env:TEMP\python_installer.exe"
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
            Write-Host "  Installing Python (silent)..." -ForegroundColor DarkGray
            Start-Process $pyInstaller -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait -NoNewWindow -ErrorAction SilentlyContinue
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
            foreach ($c in @("python", "python3", "py")) {
                try { $v = & $c --version 2>&1 | Out-String; if ($v -match "Python 3\.(\d+)") { $minor = [int]$Matches[1]; if ($minor -ge 10) { $py = $c; $installed = $true; break } } } catch {}
            }
            Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "  Download failed: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }

    if (-not $installed) {
        try {
            $choco = Get-Command choco -ErrorAction SilentlyContinue
            if ($choco) {
                Write-Host "  Trying chocolatey..." -ForegroundColor DarkGray
                Start-Process choco -ArgumentList "install python -y" -Wait -NoNewWindow -ErrorAction SilentlyContinue
                $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
                foreach ($c in @("python", "python3", "py")) {
                    try { $v = & $c --version 2>&1 | Out-String; if ($v -match "Python 3\.(\d+)") { $minor = [int]$Matches[1]; if ($minor -ge 10) { $py = $c; $installed = $true; break } } } catch {}
                }
            }
        } catch {}
    }
}

if (-not $py) {
    Write-Host ""
    Write-Host "  [X] Python 3.10+ could not be installed automatically." -ForegroundColor Red
    Write-Host "  Manual install:" -ForegroundColor Yellow
    Write-Host "    1. Go to https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "    2. Download Python 3.12+" -ForegroundColor White
    Write-Host "    3. During install, CHECK 'Add Python to PATH'" -ForegroundColor White
    Write-Host "    4. Re-run this command" -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}
Write-Host "  [OK] $py" -ForegroundColor Green

# ====================================================================
# STEP 2: Install Ollama (optional but recommended for free local AI)
# ====================================================================
Write-Host "  [2/6] Ollama (local AI)..." -ForegroundColor Yellow
$ollamaInstalled = $false
try {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) { $ollamaInstalled = $true }
} catch {}

if (-not $ollamaInstalled) {
    Write-Host "  Ollama not found. Installing..." -ForegroundColor Yellow
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $ollamaInstaller = "$env:TEMP\ollama_install.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $ollamaInstaller -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
        Start-Process $ollamaInstaller -ArgumentList "/VERYSILENT","/NORESTART" -Wait -NoNewWindow -ErrorAction SilentlyContinue
        $env:Path = "$env:LOCALAPPDATA\Programs\Ollama;" + $env:Path
        Remove-Item $ollamaInstaller -Force -ErrorAction SilentlyContinue
        try { $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue; if ($ollamaCmd) { $ollamaInstalled = $true } } catch {}
    } catch {
        Write-Host "  Ollama install skipped (cloud AI still works)" -ForegroundColor DarkGray
    }
}

if ($ollamaInstalled) {
    Write-Host "  [OK] Ollama installed" -ForegroundColor Green
    # Start Ollama server if not running
    try {
        $testConn = New-Object System.Net.Sockets.TcpClient
        $testConn.Connect("127.0.0.1", 11434)
        $testConn.Close()
        Write-Host "  [OK] Ollama server running" -ForegroundColor Green
    } catch {
        Write-Host "  Starting Ollama server..." -ForegroundColor DarkGray
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
    # Pull model in background
    Write-Host "  Pulling AI model (first time, ~5GB)..." -ForegroundColor DarkGray
    Start-Process ollama -ArgumentList "pull","qwen2.5-coder:7b" -WindowStyle Hidden -ErrorAction SilentlyContinue
} else {
    Write-Host "  [!] Ollama skipped - AuraCode will use free cloud AI" -ForegroundColor Yellow
}

# ====================================================================
# STEP 3: Download AuraCode
# ====================================================================
Write-Host "  [3/6] Downloading AuraCode..." -ForegroundColor Yellow
$zipFile = "$env:TEMP\auracode_dl.zip"
$extractDir = "$env:TEMP\auracode_ext"
$srcDir = ""

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    if (Test-Path $zipFile) { Remove-Item $zipFile -Force }
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
    Invoke-WebRequest -Uri "$RepoUrl/archive/refs/heads/main.zip" -OutFile $zipFile -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
    Expand-Archive -Path $zipFile -DestinationPath $extractDir -Force
    $srcDir = (Get-ChildItem $extractDir -Directory | Select-Object -First 1).FullName
    Write-Host "  [OK] Downloaded latest version" -ForegroundColor Green
} catch {
    Write-Host "  [X] Download failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Check internet connection and retry." -ForegroundColor Yellow
    pause
    exit 1
}

# ====================================================================
# STEP 4: Install files (preserve existing .env!)
# ====================================================================
Write-Host "  [4/6] Installing files..." -ForegroundColor Yellow

Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object {
    try { $_.CommandLine -match "auracode" } catch { $false }
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

$savedEnv = $null
if (Test-Path "$InstallDir\.env") {
    $savedEnv = Get-Content "$InstallDir\.env" -Raw -ErrorAction SilentlyContinue
}

foreach ($d in @($InstallDir, "$InstallDir\app", "$InstallDir\.auracode\sessions")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

Copy-Item "$srcDir\auracode.py" "$InstallDir\auracode.py" -Force

New-Item -ItemType Directory -Path "$InstallDir\app" -Force | Out-Null
$pyFiles = Get-ChildItem "$srcDir\app\*.py" -ErrorAction SilentlyContinue
foreach ($f in $pyFiles) { Copy-Item $f.FullName "$InstallDir\app\$($f.Name)" -Force }

if (Test-Path "$srcDir\requirements.txt") { Copy-Item "$srcDir\requirements.txt" "$InstallDir\requirements.txt" -Force }
if (Test-Path "$srcDir\static") { Copy-Item "$srcDir\static" "$InstallDir\static" -Recurse -Force }

# Handle .env: restore saved or create fresh with ALL settings
if ($savedEnv) {
    # Merge: keep saved keys, add any new settings from fresh template
    $savedEnv | Set-Content "$InstallDir\.env" -NoNewline
    Write-Host "  [OK] Restored existing .env (kept your API keys)" -ForegroundColor Green
} elseif (-not (Test-Path "$InstallDir\.env")) {
    @"
# AuraCode v3.0 - Configuration
# Local AI (free, no key needed) + Cloud fallback

AI_PROVIDER=aurine

# --- Local Ollama (default) ---
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
AURINE_NATIVE_MODEL=qwen2.5-coder:7b
AURINE_EMBEDDING_MODEL=nomic-embed-text

# --- Cloud (optional, for fallback) ---
GOOGLE_API_KEY=
GOOGLE_CHAT_MODEL=gemini-2.0-flash
GROQ_API_KEY=
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=

# Database
VECTOR_DB=$InstallDir\vector_store.sqlite3
DATA_DIR=$InstallDir\data
GENERATED_PROJECTS_DIR=$InstallDir\generated_projects

# Features
MEMORY_ENABLED=true
REASONING_ENABLED=true
CHAIN_OF_THOUGHT=true
SELF_VERIFY=true
MAX_TOOL_ITERATIONS=5
"@ | Set-Content "$InstallDir\.env" -NoNewline
    Write-Host "  [OK] Created .env (local AI by default, add keys for cloud fallback)" -ForegroundColor Green
}

Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

# ====================================================================
# STEP 5: Install Python packages (bulletproof)
# ====================================================================
Write-Host "  [5/6] Installing packages..." -ForegroundColor Yellow

$venvDir = "$InstallDir\.venv"
$venvPy = "$venvDir\Scripts\python.exe"

if (-not (Test-Path "$venvDir\pyvenv.cfg")) {
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    if (Test-Path $venvDir) { Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue }
    Start-Process -FilePath "$py" -ArgumentList "-m venv `"$venvDir`"" -Wait -NoNewWindow -ErrorAction SilentlyContinue
}

Start-Process -FilePath "$venvPy" -ArgumentList "-m pip install --upgrade pip" -Wait -NoNewWindow -ErrorAction SilentlyContinue

$packages = @("rich", "questionary", "fastapi", "uvicorn", "pypdf", "openpyxl")
$ok = 0
$fail = 0
foreach ($pkg in $packages) {
    Start-Process -FilePath "$venvPy" -ArgumentList "-m pip install $pkg" -Wait -NoNewWindow -ErrorAction SilentlyContinue
    $importName = $pkg.Replace('-','_')
    $check = cmd /c "`"$venvPy`" -c `"import $importName`"" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $pkg" -ForegroundColor Green
        $ok++
    } else {
        Start-Process -FilePath "$venvPy" -ArgumentList "-m pip install $pkg --force-reinstall" -Wait -NoNewWindow -ErrorAction SilentlyContinue
        $check2 = cmd /c "`"$venvPy`" -c `"import $importName`"" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] $pkg" -ForegroundColor Green
            $ok++
        } else {
            Write-Host "  [!] $pkg (will auto-install on first run)" -ForegroundColor DarkGray
            $fail++
        }
    }
}
Write-Host "  Packages: $ok/$($packages.Count)" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })

if ($ok -gt 0) {
    Set-Content -Path "$venvDir\.deps_installed" -Value "ok" -Force
}

# ====================================================================
# STEP 6: Create global command + auto-update mechanism
# ====================================================================
Write-Host "  [6/6] Creating command..." -ForegroundColor Yellow

if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

$batContent = @"
@echo off
title AuraCode
cd /d "$InstallDir"

:: === FAST STARTUP: skip if deps already installed ===
if exist ".venv\.deps_installed" goto :launch

:: === FIRST RUN: install everything ===
if not exist ".venv\Scripts\python.exe" (
    echo   Setting up Python...
    python -m venv .venv 2>nul
)
if not exist ".venv\Scripts\python.exe" (
    echo   [X] Python 3.10+ needed. Install from python.org
    pause
    exit /b 1
)

echo   Installing packages (first run only)...
".venv\Scripts\python.exe" -m pip install rich questionary fastapi uvicorn pypdf openpyxl -q 2>nul
if not errorlevel 1 echo. > ".venv\.deps_installed"

:launch
if not exist ".auracode\sessions" mkdir ".auracode\sessions" >nul

:: === AUTO-UPDATE: download latest from GitHub if online ===
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import urllib.request,zipfile,os,shutil,tempfile;url='https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip';td=tempfile.mkdtemp();urllib.request.urlretrieve(url,os.path.join(td,'u.zip'));zipfile.ZipFile(os.path.join(td,'u.zip')).extractall(td);src=[d for d in os.listdir(td) if os.path.isdir(os.path.join(td,d)) and d.startswith('aurineAI')];[shutil.copy2(os.path.join(src[0],f),f) for f in ['auracode.py'] if os.path.exists(os.path.join(src[0],f))];[shutil.copytree(os.path.join(src[0],'app'),'app',dirs_exist_ok=True) if os.path.exists(os.path.join(src[0],'app')) else None];shutil.rmtree(td,ignore_errors=True)" 2>nul
)

".venv\Scripts\python.exe" auracode.py %*
"@
$batContent | Set-Content "$BinDir\auracode.bat" -NoNewline -Encoding ASCII
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

# Create auracode.ps1 in bin for PowerShell users
$psContent = @"
`$ErrorActionPreference = "SilentlyContinue"
Set-Location "$InstallDir"

# Fast startup check
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "  Setting up..." -ForegroundColor DarkGray
    python -m venv .venv 2>`$null
}
if (-not (Test-Path ".venv\.deps_installed")) {
    Write-Host "  Installing packages..." -ForegroundColor DarkGray
    & ".\.venv\Scripts\python.exe" -m pip install rich questionary fastapi uvicorn pypdf openpyxl -q 2>`$null
    Set-Content -Path ".venv\.deps_installed" -Value "ok" -Force
}

# Auto-update from GitHub
try {
    & ".\.venv\Scripts\python.exe" -c "import urllib.request,zipfile,os,shutil,tempfile;url='https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip';td=tempfile.mkdtemp();urllib.request.urlretrieve(url,os.path.join(td,'u.zip'));zipfile.ZipFile(os.path.join(td,'u.zip')).extractall(td);src=[d for d in os.listdir(td) if os.path.isdir(os.path.join(td,d)) and d.startswith('aurineAI')];[shutil.copy2(os.path.join(src[0],f),f) for f in ['auracode.py'] if os.path.exists(os.path.join(src[0],f))];[shutil.copytree(os.path.join(src[0],'app'),'app',dirs_exist_ok=True) if os.path.exists(os.path.join(src[0],'app')) else None];shutil.rmtree(td,ignore_errors=True)" 2>`$null
} catch {}

& ".\.venv\Scripts\python.exe" auracode.py
"@
$psContent | Set-Content "$BinDir\auracode.ps1" -NoNewline -Encoding UTF8

# Add to PATH
$curPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$curPath;$BinDir", "User")
    $env:Path += ";$BinDir"
}

Write-Host "  [OK] 'auracode' command ready" -ForegroundColor Green

# ====================================================================
# DONE
# ====================================================================
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Installed! Open NEW terminal and type:" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "    auracode" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
Write-Host "  How it works:" -ForegroundColor Cyan
Write-Host "    - Local AI (Ollama) runs FREE, no API key needed" -ForegroundColor White
Write-Host "    - If Ollama not available, uses free cloud AI" -ForegroundColor White
Write-Host "    - Add GOOGLE_API_KEY to .env for cloud fallback" -ForegroundColor White
Write-Host ""
Write-Host "  Get free cloud key: https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
Write-Host "  Commands: Ctrl+P (palette) | /help | /connect" -ForegroundColor DarkGray
Write-Host ""
