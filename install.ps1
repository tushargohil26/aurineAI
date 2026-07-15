# AuraCode Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex

$InstallDir = "$env:USERPROFILE\.aurine"
$BinDir = "$InstallDir\bin"

Write-Host ""
Write-Host "  AuraCode Installer" -ForegroundColor Cyan
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

# 2) Download AuraCode
Write-Host "  [2/3] Downloading AuraCode..." -ForegroundColor Yellow

# Remove old install if exists
if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue }

# Download zip from GitHub
$zipUrl = "https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip"
$zipFile = "$env:TEMP\auracode-install.zip"
$extractDir = "$env:TEMP\auracode-extract"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing
} catch {
    Write-Host "  [x] Download failed: $_" -ForegroundColor Red
    exit 1
}

# Extract
if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
Expand-Archive -Path $zipFile -DestinationPath $extractDir -Force

# Move to install dir
$srcDir = Get-ChildItem $extractDir -Directory | Select-Object -First 1
if (-not $srcDir) { Write-Host "  [x] Extract failed" -ForegroundColor Red; exit 1 }
Move-Item $srcDir.FullName $InstallDir -Force

# Cleanup temp
Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "  Downloaded OK" -ForegroundColor Green

# 3) Setup venv + deps + launcher
Write-Host "  [3/3] Setting up..." -ForegroundColor Yellow

# Init git so future updates work
Set-Location $InstallDir
& git init -q 2>$null
& git remote add origin https://github.com/tushargohil26/aurineAI.git 2>$null
& git add -A 2>$null
& git commit -m "init" -q 2>$null

# Create venv
if (-not (Test-Path ".venv")) {
    & $py -m venv .venv
}

# Install deps
$venvPy = "$InstallDir\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    & $venvPy -m pip install --upgrade pip -q 2>$null
    if (Test-Path "requirements.txt") {
        & $venvPy -m pip install -r requirements.txt -q 2>$null
    }
}
Write-Host "  Dependencies OK" -ForegroundColor Green

# Create bin dir
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

# Inner launcher
$innerBat = @"
@echo off
cd /d "$InstallDir"
title AuraCode
.venv\Scripts\python.exe auracode.py
if errorlevel 1 (
    echo.
    echo  AuraCode crashed. Make sure Python 3.10+ is installed.
    pause
)
"@
Set-Content "$BinDir\_auracode_inner.bat" $innerBat -NoNewline

# Outer launcher
$outerBat = @"
@echo off
start "AuraCode" cmd /k "$BinDir\_auracode_inner.bat"
"@
Set-Content "$BinDir\auracode.bat" $outerBat -NoNewline
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
