@echo off
:: AuraCode Setup - Run once, then 'auracode' works from any terminal
echo.
echo   AuraCode Setup
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0setup-auracode.ps1"
echo.
pause
