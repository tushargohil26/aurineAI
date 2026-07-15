# AuraCode One-Line Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  AuraCode Installer" -ForegroundColor Cyan
Write-Host "  =================" -ForegroundColor Cyan
Write-Host ""

# Config
$Repo = "https://github.com/tushargohil26/aurineAI.git"
$InstallDir = "$env:USERPROFILE\aurine-ai-assistant"
$AuracodeDir = "$env:USERPROFILE\.auracode"

# Step 1: Check Python
Write-Host "  [1/5] Checking Python..." -ForegroundColor Yellow
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.\d+") {
            $python = $cmd
            Write-Host "        Found: $ver" -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $python) {
    Write-Host "        Python 3 not found!" -ForegroundColor Red
    Write-Host "        Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "        Make sure to check 'Add Python to PATH' during install." -ForegroundColor Yellow
    exit 1
}

# Step 2: Check Git
Write-Host "  [2/5] Checking Git..." -ForegroundColor Yellow
$git = $null
try {
    $gitVer = & git --version 2>&1
    $git = "git"
    Write-Host "        Found: $gitVer" -ForegroundColor Green
} catch {
    Write-Host "        Git not found!" -ForegroundColor Red
    Write-Host "        Install from: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Step 3: Clone or update repo
Write-Host "  [3/5] Getting Aurine AI..." -ForegroundColor Yellow
if (Test-Path "$InstallDir\.git") {
    Write-Host "        Updating existing installation..." -ForegroundColor Green
    Set-Location $InstallDir
    & git pull origin main 2>&1 | Out-Null
} else {
    Write-Host "        Cloning repository..." -ForegroundColor Green
    & git clone $Repo $InstallDir 2>&1 | Out-Null
}
Set-Location $InstallDir

# Step 4: Setup venv and install dependencies
Write-Host "  [4/5] Installing dependencies..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    & $python -m venv .venv 2>&1 | Out-Null
}
$pip = ".venv\Scripts\pip.exe"
& $pip install --upgrade pip -q 2>&1 | Out-Null
if (Test-Path "requirements.txt") {
    & $pip install -r requirements.txt -q 2>&1 | Out-Null
}
Write-Host "        Done" -ForegroundColor Green

# Step 5: Install auracode command
Write-Host "  [5/5] Installing 'auracode' command..." -ForegroundColor Yellow
if (-not (Test-Path $AuracodeDir)) {
    New-Item -ItemType Directory -Path $AuracodeDir -Force | Out-Null
}

# Create launcher bat
$batContent = @"
@echo off
title AuraCode - AI Terminal Agent
set "AURINE_DIR=$InstallDir"
cd /d "%AURINE_DIR%"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" auracode.py
) else (
    echo [AuraCode] Setup incomplete. Run installer again.
    pause
)
"@
Set-Content -Path "$AuracodeDir\auracode.bat" -Value $batContent

# Create launcher ps1
$ps1Content = @"
`$ErrorActionPreference = "Stop"
`$AurineDir = "$InstallDir"
`$Python = Join-Path `$AurineDir ".venv\Scripts\python.exe"
`$Script = Join-Path `$AurineDir "auracode.py"
if (-not (Test-Path `$Python)) {
    Write-Host "[AuraCode] Setup incomplete. Run installer again." -ForegroundColor Red
    exit 1
}
Set-Location `$AurineDir
& `$Python `$Script
"@
Set-Content -Path "$AuracodeDir\auracode.ps1" -Value $ps1Content

# Create launcher cmd
Copy-Item "$AuracodeDir\auracode.bat" "$AuracodeDir\auracode.cmd" -Force

# Add to PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$AuracodeDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$AuracodeDir", "User")
    $env:Path += ";$AuracodeDir"
}
Write-Host "        Done" -ForegroundColor Green

# Add PowerShell function
$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}
$existing = ""
if (Test-Path $profilePath) { $existing = Get-Content $profilePath -Raw }
if ($existing -notlike "*auracode*") {
    Add-Content -Path $profilePath -Value ""
    Add-Content -Path $profilePath -Value "# AuraCode"
    Add-Content -Path $profilePath -Value "function auracode { & `"$AuracodeDir\auracode.ps1`" @args }"
}

# Add bash alias
$bashrc = "$env:USERPROFILE\.bashrc"
$aliasLine = "alias auracode='cmd.exe /c `"$AuracodeDir\auracode.bat`"'"
if (Test-Path $bashrc) {
    $bContent = Get-Content $bashrc -Raw
    if ($bContent -notlike "*auracode*") {
        Add-Content -Path $bashrc -Value ""
        Add-Content -Path $bashrc -Value "# AuraCode"
        Add-Content -Path $bashrc -Value $aliasLine
    }
} else {
    Set-Content -Path $bashrc -Value "# AuraCode"
    Add-Content -Path $bashrc -Value $aliasLine
}

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  AuraCode installed successfully!" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Installed to: $InstallDir" -ForegroundColor White
Write-Host "  Command:      auracode" -ForegroundColor White
Write-Host ""
Write-Host "  To use:" -ForegroundColor Cyan
Write-Host "    1. Close this terminal" -ForegroundColor White
Write-Host "    2. Open a NEW terminal" -ForegroundColor White
Write-Host "    3. Type: auracode" -ForegroundColor White
Write-Host ""
