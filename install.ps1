# AuraCode - Minimal AI Terminal Agent Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex

$InstallDir = "$env:USERPROFILE\.aurine"
$BinDir = "$InstallDir\bin"

Write-Host ""
Write-Host "  AuraCode Installer" -ForegroundColor Cyan
Write-Host "  (AI terminal agent - lightweight install)" -ForegroundColor DarkGray
Write-Host ""

# 1) Check Python
$py = $null
foreach ($c in @("python","python3","py")) {
    try { $v = & $c --version 2>&1; if ($v -match "Python 3") { $py = $c; break } } catch {}
}
if (-not $py) {
    Write-Host "  [x] Python 3 not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  [1/3] Python OK" -ForegroundColor Green

# 2) Download only essential files
Write-Host "  [2/3] Downloading AuraCode..." -ForegroundColor Yellow

$zipUrl = "https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip"
$zipFile = "$env:TEMP\auracode.zip"
$extractDir = "$env:TEMP\auracode-extract"

# Download zip
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing
} catch {
    Write-Host "  [x] Download failed" -ForegroundColor Red
    exit 1
}

# Extract
if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -Path $zipFile -DestinationPath $extractDir -Force

$srcDir = (Get-ChildItem $extractDir -Directory | Select-Object -First 1).FullName

# Create clean install dir with ONLY auracode files
# Kill any running python to unlock files
Get-Process python,pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $InstallDir) { cmd /c "rd /s /q `"$InstallDir`"" 2>$null }
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallDir\app" -Force | Out-Null

# Copy ONLY what auracode needs
Copy-Item "$srcDir\auracode.py" "$InstallDir\auracode.py" -Force
Copy-Item "$srcDir\app\__init__.py" "$InstallDir\app\__init__.py" -Force
Copy-Item "$srcDir\app\llm.py" "$InstallDir\app\llm.py" -Force
Copy-Item "$srcDir\app\config.py" "$InstallDir\app\config.py" -Force
Copy-Item "$srcDir\app\device.py" "$InstallDir\app\device.py" -Force

# Copy .env example
if (Test-Path "$srcDir\.env.example") {
    Copy-Item "$srcDir\.env.example" "$InstallDir\.env.example" -Force
    if (-not (Test-Path "$InstallDir\.env")) {
        Copy-Item "$srcDir\.env.example" "$InstallDir\.env" -Force
    }
}

# Cleanup temp
Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "  Downloaded OK" -ForegroundColor Green

# 3) Create venv + install ONLY needed packages
Write-Host "  [3/3] Setting up..." -ForegroundColor Yellow

# Create venv
$venvDir = "$InstallDir\.venv"
if (-not (Test-Path "$venvDir\pyvenv.cfg")) {
    # Kill python again in case something started
    Get-Process python,pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500

    # Force remove old broken venv
    if (Test-Path $venvDir) {
        Remove-Item $venvDir -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $venvDir) { cmd /c "rd /s /q `"$venvDir`"" 2>$null }
    }

    # Create fresh venv in temp first, then move
    $tmpVenv = "$env:TEMP\auracode_venv"
    if (Test-Path $tmpVenv) { Remove-Item $tmpVenv -Recurse -Force -ErrorAction SilentlyContinue }
    & $py -m venv $tmpVenv

    if (Test-Path "$tmpVenv\pyvenv.cfg") {
        Move-Item $tmpVenv $venvDir -Force
    } else {
        # Fallback: create directly
        & $py -m venv $venvDir
    }
}

# Install ONLY the 4 packages auracode needs
$venvPy = "$InstallDir\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    & $venvPy -m pip install openai httpx pydantic python-dotenv -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [!] pip install had issues, retrying..." -ForegroundColor Yellow
        & $venvPy -m pip install openai httpx pydantic python-dotenv
    }
} else {
    Write-Host "  [x] venv python not found at $venvPy" -ForegroundColor Red
    Write-Host "  Try running: python -m venv `"$InstallDir\.venv`"" -ForegroundColor Yellow
}

Write-Host "  Dependencies OK" -ForegroundColor Green

# Create launchers
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

# Inner launcher
@"
@echo off
cd /d "$InstallDir"
title AuraCode
.venv\Scripts\python.exe auracode.py
if errorlevel 1 (
    echo.
    echo  AuraCode crashed. Make sure Python 3.10+ is installed.
    pause
)
"@ | Set-Content "$BinDir\_auracode_inner.bat" -NoNewline

# Outer launcher
@"
@echo off
start "AuraCode" cmd /k "$BinDir\_auracode_inner.bat"
"@ | Set-Content "$BinDir\auracode.bat" -NoNewline
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

# Add to PATH
$curPath = [Environment]::GetEnvironmentVariable("Path","User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path","$curPath;$BinDir","User")
}

Write-Host "  Done!" -ForegroundColor Green
Write-Host ""
Write-Host "  Open a NEW terminal and type:" -ForegroundColor White
Write-Host "    auracode" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
