@echo off
title AuraCode - AI Terminal Agent
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" auracode.py
) else (
    echo [AuraCode] Python venv not found. Run: irm https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.ps1 ^| iex
    pause
)
