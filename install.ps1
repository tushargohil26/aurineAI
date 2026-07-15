# AuraCode Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

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
Write-Host "  [1/4] Python OK" -ForegroundColor Green

# 2) Check Git
try { & git --version 2>&1 | Out-Null } catch {
    Write-Host "  [x] Git not found. Install from https://git-scm.com" -ForegroundColor Red
    exit 1
}
Write-Host "  [2/4] Git OK" -ForegroundColor Green

# 3) Clone / Pull repo
Write-Host "  [3/4] Downloading AuraCode..." -ForegroundColor Yellow
if (Test-Path "$InstallDir\.git") {
    Set-Location $InstallDir
    & git fetch origin main -q 2>$null
    & git reset --hard origin/main -q 2>$null
} else {
    if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
    & git clone https://github.com/tushargohil26/aurineAI.git $InstallDir 2>$null
}
Set-Location $InstallDir

# Create venv if missing (skip if already exists)
if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    & $py -m venv .venv
}

# Install deps
$venvPy = "$InstallDir\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    & $venvPy -m pip install --upgrade pip -q 2>$null
    if (Test-Path "requirements.txt") {
        & $venvPy -m pip install -r requirements.txt -q 2>$null
    }
    Write-Host "  Dependencies OK" -ForegroundColor Green
} else {
    Write-Host "  [!] venv python not found at $venvPy" -ForegroundColor Red
}

# 4) Create launcher
Write-Host "  [4/4] Installing auracode command..." -ForegroundColor Yellow
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

# Inner launcher - runs inside the new terminal
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

# Outer launcher - opens NEW terminal window
$outerBat = @"
@echo off
start "AuraCode" cmd /k "$BinDir\_auracode_inner.bat"
"@
Set-Content "$BinDir\auracode.bat" $outerBat -NoNewline
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

# PowerShell function in profile
$prof = $PROFILE.CurrentUserAllHosts
$profDir = Split-Path $prof
if (-not (Test-Path $profDir)) { New-Item -ItemType Directory -Path $profDir -Force | Out-Null }
$ex = if (Test-Path $prof) { Get-Content $prof -Raw } else { "" }
if ($ex -notlike "*function auracode*") {
    $funcDef = "`nfunction auracode { Start-Process cmd -ArgumentList '/k','`"$BinDir\_auracode_inner.bat`"' }"
    Add-Content $prof $funcDef
}

# Add to PATH
$curPath = [Environment]::GetEnvironmentVariable("Path","User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path","$curPath;$BinDir","User")
    $env:Path += ";$BinDir"
}

# Remove old broken PATH entries
$oldPaths = @("$env:USERPROFILE\.auracode")
foreach ($op in $oldPaths) {
    if ($curPath -like "*$op*") {
        $cleaned = ($curPath -split ";" | Where-Object { $_ -ne $op }) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $cleaned, "User")
        $curPath = $cleaned
    }
}

Write-Host "  Done!" -ForegroundColor Green
Write-Host ""
Write-Host "  Open a NEW terminal and type:" -ForegroundColor White
Write-Host "    auracode" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
