@echo off
title AuraCode
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" auracode.py
) else (
    echo.
    echo  AuraCode not installed. Run:
    echo  irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 ^| iex
    echo.
    pause
)
