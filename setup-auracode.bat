@echo off
:: AuraCode Setup - Run once
echo.
echo   AuraCode Setup
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0setup-auracode.ps1"
echo.
pause
