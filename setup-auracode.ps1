# AuraCode Setup - Run once to enable 'auracode' command in ALL terminals
# Run: powershell -ExecutionPolicy Bypass -File setup-auracode.ps1

$ErrorActionPreference = "Stop"
$InstallDir = "$env:USERPROFILE\.auracode"
$ProjectDir = $PSScriptRoot

Write-Host ""
Write-Host "  AuraCode Setup" -ForegroundColor Cyan
Write-Host "  Installing launchers to: $InstallDir"
Write-Host ""

# Create install directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# Copy all launcher files
$files = @("auracode.bat", "auracode.ps1", "auracode")
foreach ($f in $files) {
    $src = Join-Path $ProjectDir $f
    $dst = Join-Path $InstallDir $f
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Host "  [ok] $f" -ForegroundColor Green
    }
}

# Add to user PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$InstallDir", "User")
    $env:Path += ";$InstallDir"
    Write-Host ""
    Write-Host "  Added to PATH: $InstallDir" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Already in PATH" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Done! Open a NEW terminal and type: auracode" -ForegroundColor Cyan
Write-Host ""
