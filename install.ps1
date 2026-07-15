# AuraCode Installer
# Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$InstallDir = "$env:USERPROFILE\.aurine"
$BinDir = "$env:USERPROFILE\.aurine\bin"

Write-Host ""
Write-Host "  AuraCode Installer" -ForegroundColor Cyan
Write-Host ""

# Check Python
$py = $null
foreach ($c in @("python","python3","py")) { try { $v = & $c --version 2>&1; if ($v -match "Python 3") { $py = $c; break } } catch {} }
if (-not $py) { Write-Host "  Python 3 not found. Install from python.org" -ForegroundColor Red; exit 1 }
Write-Host "  [1/4] Python OK" -ForegroundColor Green

# Check Git
try { & git --version 2>&1 | Out-Null } catch { Write-Host "  Git not found. Install from git-scm.com" -ForegroundColor Red; exit 1 }
Write-Host "  [2/4] Git OK" -ForegroundColor Green

# Clone
Write-Host "  [3/4] Downloading..." -ForegroundColor Yellow
if (Test-Path "$InstallDir\.git") { Set-Location $InstallDir; & git pull -q 2>$null }
else { & git clone https://github.com/tushargohil26/aurineAI.git $InstallDir 2>$null }
Set-Location $InstallDir
if (-not (Test-Path ".venv")) { & $py -m venv .venv 2>$null }
& "$InstallDir\.venv\Scripts\pip.exe" install -r requirements.txt -q 2>$null
Write-Host "  Done" -ForegroundColor Green

# Install command
Write-Host "  [4/4] Installing auracode..." -ForegroundColor Yellow
if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir -Force | Out-Null }

# CMD launcher (opens NEW window)
@"
@echo off
start "" /D "$InstallDir" cmd /k "title AuraCode && cd /d "$InstallDir" && ".venv\Scripts\python.exe" auracode.py"
"@ | Set-Content "$BinDir\auracode.bat" -NoNewline

# Copy as .cmd too
Copy-Item "$BinDir\auracode.bat" "$BinDir\auracode.cmd" -Force

# PowerShell launcher (opens NEW window)
@"
Start-Process cmd -ArgumentList '/k','title AuraCode && cd /d \"$InstallDir\" && \"$InstallDir\.venv\Scripts\python.exe\" auracode.py'
"@ | Set-Content "$BinDir\auracode.ps1" -NoNewline

# Add to PATH
$curPath = [Environment]::GetEnvironmentVariable("Path","User")
if ($curPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path","$curPath;$BinDir","User")
    $env:Path += ";$BinDir"
}

# PowerShell function in profile
$prof = $PROFILE.CurrentUserAllHosts
$profDir = Split-Path $prof
if (-not (Test-Path $profDir)) { New-Item -ItemType Directory -Path $profDir -Force | Out-Null }
$ex = if (Test-Path $prof) { Get-Content $prof -Raw } else { "" }
if ($ex -notlike "*function auracode*") {
    Add-Content $prof "`nfunction auracode { Start-Process cmd -ArgumentList '/k','title AuraCode && cd /d `"$InstallDir`" && `"$InstallDir\.venv\Scripts\python.exe`" auracode.py' }"
}

# Bash alias
$brc = "$env:USERPROFILE\.bashrc"
$al = "alias auracode='cmd.exe /c start `"`" cmd /k `"cd /d $InstallDir && .venv/Scripts/python.exe auracode.py`"'"
if (Test-Path $brc) { $b = Get-Content $brc -Raw; if ($b -notlike "*auracode*") { Add-Content $brc "`n$al" } }
else { Set-Content $brc $al }

Write-Host "  Done" -ForegroundColor Green
Write-Host ""
Write-Host "  Installed! Open a NEW terminal and type:" -ForegroundColor Green
Write-Host "    auracode" -ForegroundColor White -BackgroundColor DarkGreen
Write-Host ""
