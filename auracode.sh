#!/bin/bash
# AuraCode Auto-Update Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Auto-update from GitHub
if [ -d ".git" ]; then
    echo "  Checking for updates..."
    git pull origin main --quiet 2>/dev/null
fi

# Ensure .env
if [ ! -f ".env" ]; then
    [ -f ".env.example" ] && cp .env.example .env
fi

# Ensure venv
if [ ! -f ".venv/bin/python" ] && [ ! -f ".venv/Scripts/python.exe" ]; then
    python3 -m venv .venv 2>/dev/null || python -m venv .venv 2>/dev/null
fi

# Install deps
if [ -f ".venv/bin/pip" ]; then
    .venv/bin/pip install -r requirements.txt -q 2>/dev/null
    .venv/bin/python auracode.py
elif [ -f ".venv/Scripts/pip.exe" ]; then
    .venv/Scripts/pip.exe install -r requirements.txt -q 2>/dev/null
    .venv/Scripts/python.exe auracode.py
else
    echo "[AuraCode] Python not found. Install Python 3.10+"
    exit 1
fi
