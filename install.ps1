# AuraCode v2.1 - Universal Installer (v2.1.0 - cache bust)
# Run on ANY Windows device: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex

$InstallDir = "$env:USERPROFILE\.aurine"
$BinDir = "$InstallDir\bin"
$RepoUrl = "https://github.com/tushargohil26/aurineAI"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    AuraCode v2.0 - AI Terminal Agent" -ForegroundColor Cyan
Write-Host "    Works on ANY device | No Ollama needed" -ForegroundColor DarkGray
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# ====================================================================
# STEP 1: Find or Install Python (NEVER crash, auto-install)
# ====================================================================
Write-Host "  [1/5] Python..." -ForegroundColor Yellow
$py = $null

# Check existing Python
foreach ($c in @("python", "python3", "py")) {
    try {
        $v = & $c --version 2>&1 | Out-String
        if ($v -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) { $py = $c; break }
        }
    } catch {}
}

# Not found - try to install automatically
if (-not $py) {
    Write-Host "  Python not found. Installing automatically..." -ForegroundColor Yellow

    # Method 1: Try winget
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

    # Method 2: Download Python installer directly from python.org
    if (-not $installed) {
        Write-Host "  Downloading Python from python.org..." -ForegroundColor DarkGray
        $pyUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        $pyInstaller = "$env:TEMP\python_installer.exe"
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing -TimeoutSec 120 -ErrorAction Stop
            Write-Host "  Installing Python (silent)..." -ForegroundColor DarkGray
            Start-Process $pyInstaller -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait -NoNewWindow -ErrorAction SilentlyContinue
            # Refresh PATH
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
            foreach ($c in @("python", "python3", "py")) {
                try { $v = & $c --version 2>&1 | Out-String; if ($v -match "Python 3\.(\d+)") { $minor = [int]$Matches[1]; if ($minor -ge 10) { $py = $c; $installed = $true; break } } } catch {}
            }
            Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "  Download failed: $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }

    # Method 3: Try choco
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
# STEP 2: Download AuraCode
# ====================================================================
Write-Host "  [2/5] Downloading..." -ForegroundColor Yellow
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
    Write-Host "  [OK] Downloaded" -ForegroundColor Green
} catch {
    Write-Host "  [X] Download failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Check internet connection and retry." -ForegroundColor Yellow
    pause
    exit 1
}

# ====================================================================
# STEP 3: Install files (preserve existing .env!)
# ====================================================================
Write-Host "  [3/5] Installing files..." -ForegroundColor Yellow

# Stop any running instance
Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object {
    try { $_.CommandLine -match "auracode" } catch { $false }
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# Save existing .env before overwriting
$savedEnv = $null
if (Test-Path "$InstallDir\.env") {
    $savedEnv = Get-Content "$InstallDir\.env" -Raw -ErrorAction SilentlyContinue
}

# Create directories
foreach ($d in @($InstallDir, "$InstallDir\app", "$InstallDir\.auracode\sessions")) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# Copy auracode.py
Copy-Item "$srcDir\auracode.py" "$InstallDir\auracode.py" -Force

# Copy app/ module
New-Item -ItemType Directory -Path "$InstallDir\app" -Force | Out-Null
$pyFiles = Get-ChildItem "$srcDir\app\*.py" -ErrorAction SilentlyContinue
foreach ($f in $pyFiles) { Copy-Item $f.FullName "$InstallDir\app\$($f.Name)" -Force }

# Copy requirements.txt
if (Test-Path "$srcDir\requirements.txt") { Copy-Item "$srcDir\requirements.txt" "$InstallDir\requirements.txt" -Force }

# Handle .env: restore saved or create new
if ($savedEnv) {
    $savedEnv | Set-Content "$InstallDir\.env" -NoNewline
    Write-Host "  [OK] Restored existing .env (kept your API keys)" -ForegroundColor Green
} elseif (-not (Test-Path "$InstallDir\.env")) {
    # Try to copy from source repo
    $srcEnv = Join-Path $srcDir ".env"
    if (Test-Path $srcEnv) {
        Copy-Item $srcEnv "$InstallDir\.env" -Force
    } else {
        @"
AI_PROVIDER=aurine
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
    Write-Host "  [OK] Created .env" -ForegroundColor Green
}

# Cleanup
Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

# ====================================================================
# STEP 4: Install Python packages (bulletproof)
# ====================================================================
Write-Host "  [4/5] Installing packages..." -ForegroundColor Yellow

$venvDir = "$InstallDir\.venv"
$venvPy = "$venvDir\Scripts\python.exe"

# Create venv if missing
if (-not (Test-Path "$venvDir\pyvenv.cfg")) {
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    if (Test-Path $venvDir) { Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue }
    Start-Process -FilePath "$py" -ArgumentList "-m venv `"$venvDir`"" -Wait -NoNewWindow -ErrorAction SilentlyContinue
}

# Upgrade pip
Start-Process -FilePath "$venvPy" -ArgumentList "-m pip install --upgrade pip" -Wait -NoNewWindow -ErrorAction SilentlyContinue

# Install packages one by one (NEVER crash)
$packages = @("rich", "questionary", "openai", "httpx", "pydantic", "python-dotenv", "pygments")
$ok = 0
$fail = 0
foreach ($pkg in $packages) {
    Start-Process -FilePath "$venvPy" -ArgumentList "-m pip install $pkg" -Wait -NoNewWindow -ErrorAction SilentlyContinue
    $check = cmd /c "`"$venvPy`" -c `"import $($pkg.Replace('-','_'))`"" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $pkg" -ForegroundColor Green
        $ok++
    } else {
        Start-Process -FilePath "$venvPy" -ArgumentList "-m pip install $pkg --force-reinstall" -Wait -NoNewWindow -ErrorAction SilentlyContinue
        $check2 = cmd /c "`"$venvPy`" -c `"import $($pkg.Replace('-','_'))`"" 2>&1
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

# ====================================================================
# STEP 5: Create global command
# ====================================================================
Write-Host "  [5/5] Creating command..." -ForegroundColor Yellow

if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

$batContent = @"
@echo off
cd /d "$InstallDir"
if not exist ".venv\Scripts\python.exe" (
    "$py" -m venv .venv 2>nul
)
if not exist ".venv\Scripts\python.exe" (
    echo   [X] Python 3.10+ needed. Install from python.org
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q 2>nul
".venv\Scripts\python.exe" auracode.py %*
"@
$batContent | Set-Content "$BinDir\auracode.bat" -NoNewline -Encoding ASCII
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

# Add to PATH
$curPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$curPath;$BinDir", "User")
    $env:Path += ";$BinDir"
}

Write-Host "  [OK] 'auracode' ready" -ForegroundColor Green

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
Write-Host "  First run: AuraCode will auto-setup AI if needed" -ForegroundColor DarkGray
Write-Host "  Commands: Ctrl+P (palette) | /connect | /help" -ForegroundColor DarkGray
Write-Host ""
