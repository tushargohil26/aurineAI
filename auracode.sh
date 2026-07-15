#!/bin/bash
# AuraCode Bash Launcher
AURINE_DIR="/c/Users/ADMIN/Documents/Codex/2026-07-01/abhi-bhi-chat-sub-niche-ho-2/work/aurine-src/aurine-ai-assistant/aurine-ai-assistant"

# Try Windows path first (Git Bash), then Unix path (WSL)
if [ -f "$AURINE_DIR/.venv/Scripts/python.exe" ]; then
    cd "$AURINE_DIR"
    .venv/Scripts/python.exe auracode.py
elif [ -f "$AURINE_DIR/.venv/bin/python" ]; then
    cd "$AURINE_DIR"
    .venv/bin/python auracode.py
else
    echo "[AuraCode] Python venv not found. Run setup first."
    exit 1
fi
