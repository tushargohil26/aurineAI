# AuraCode One-Line Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  AuraCode Installer" -ForegroundColor Cyan
Write-Host "  =================" -ForegroundColor Cyan
Write-Host ""

$Repo = "https://github.com/tushargohil26/aurineAI.git"
$InstallDir = "$env:USERPROFILE\aurine-ai-assistant"
$AuracodeDir = "$env:USERPROFILE\.auracode"

# Check Python
Write-Host "  [1/5] Checking Python..." -ForegroundColor Yellow
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.\d+") { $python = $cmd; Write-Host "        Found: $ver" -ForegroundColor Green; break }
    } catch {}
}
if (-not $python) { Write-Host "        Python 3 not found! Install from python.org" -ForegroundColor Red; exit 1 }

# Check Git
Write-Host "  [2/5] Checking Git..." -ForegroundColor Yellow
try { & git --version 2>&1 | Out-Null; Write-Host "        Found: git" -ForegroundColor Green }
catch { Write-Host "        Git not found! Install from git-scm.com" -ForegroundColor Red; exit 1 }

# Clone repo
Write-Host "  [3/5] Getting Aurine AI..." -ForegroundColor Yellow
if (Test-Path "$InstallDir\.git") {
    Write-Host "        Updating..." -ForegroundColor Green
    Set-Location $InstallDir; & git pull origin main 2>$null
} else {
    Write-Host "        Cloning..." -ForegroundColor Green
    & git clone $Repo $InstallDir 2>$null
}
Set-Location $InstallDir

# Install dependencies
Write-Host "  [4/5] Installing dependencies..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) { & $python -m venv .venv 2>$null }
& "$InstallDir\.venv\Scripts\pip.exe" install --upgrade pip -q 2>$null
if (Test-Path "requirements.txt") { & "$InstallDir\.venv\Scripts\pip.exe" install -r requirements.txt -q 2>$null }
Write-Host "        Done" -ForegroundColor Green

# Install auracode command
Write-Host "  [5/5] Installing 'auracode' command..." -ForegroundColor Yellow
if (-not (Test-Path $AuracodeDir)) { New-Item -ItemType Directory -Path $AuracodeDir -Force | Out-Null }

$batContent = "@echo off`r`ntitle AuraCode - AI Terminal Agent`r`nset `"AURINE_DIR=$InstallDir`"`r`ncd /d `"%AURINE_DIR%`"`r`nif exist `".venv\Scripts\python.exe`" (`r`n    `".venv\Scripts\python.exe`" auracode.py`r`n) else (`r`n    echo [AuraCode] Not installed.`r`n    pause`r`n)"
Set-Content -Path "$AuracodeDir\auracode.bat" -Value $batContent -NoNewline
Copy-Item "$AuracodeDir\auracode.bat" "$AuracodeDir\auracode.cmd" -Force

$ps1Content = "`$ErrorActionPreference = `"Stop`"`r`n`$AurineDir = `"$InstallDir`"`r`n`$Python = Join-Path `$AurineDir `".venv\Scripts\python.exe`"`r`n`$Script = Join-Path `$AurineDir `"auracode.py`"`r`nif (-not (Test-Path `$Python)) { Write-Host `"[AuraCode] Not installed`" -ForegroundColor Red; exit 1 }`r`nSet-Location `$AurineDir`r`n& `$Python `$Script"
Set-Content -Path "$AuracodeDir\auracode.ps1" -Value $ps1Content -NoNewline

# Add to PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$AuracodeDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$AuracodeDir", "User")
    $env:Path += ";$AuracodeDir"
}

# PowerShell profile function
$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath
if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Path $profileDir -Force | Out-Null }
$existing = if (Test-Path $profilePath) { Get-Content $profilePath -Raw } else { "" }
if ($existing -notlike "*auracode*") {
    Add-Content -Path $profilePath -Value "`n# AuraCode`nfunction auracode { & `"$AuracodeDir\auracode.ps1`" @args }"
}

# Bash alias
$bashrc = "$env:USERPROFILE\.bashrc"
$aliasLine = "alias auracode='`"$AuracodeDir\auracode.bat`"'"
if (Test-Path $bashrc) { $b = Get-Content $bashrc -Raw; if ($b -notlike "*auracode*") { Add-Content $bashrc "`n# AuraCode`n$aliasLine" } }
else { Set-Content $bashrc "# AuraCode`n$aliasLine" }

Write-Host "        Done" -ForegroundColor Green

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Installed! Close this terminal." -ForegroundColor Green
Write-Host "  Open a NEW terminal and type: auracode" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
