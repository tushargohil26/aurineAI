#!/bin/bash
# Aurine AI - One Command Install & Run
# Copy-paste this entire script into terminal to install and start Aurine
# Usage: curl -fsSL https://raw.githubusercontent.com/aurine/aurine-ai/main/install.sh | bash

set -e

AURINE_DIR="$HOME/.aurine"

echo ""
echo "  ============================================"
echo "    Aurine AI - Installing..."
echo "  ============================================"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYVER=$(python3 --version 2>&1)
    echo "  Python: $PYVER"
else
    echo "  Python3 not found. Installing..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3 python3-venv python3-pip
    elif command -v brew &> /dev/null; then
        brew install python3
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip
    else
        echo "  Please install Python 3.10+ manually: https://python.org"
        exit 1
    fi
fi

# Clone or update
if [ -d "$AURINE_DIR/app" ]; then
    echo "  Updating Aurine..."
    cd "$AURINE_DIR" && git pull 2>/dev/null || true
else
    echo "  Downloading Aurine..."
    if command -v git &> /dev/null; then
        git clone https://github.com/aurine/aurine-ai.git "$AURINE_DIR" 2>/dev/null
    else
        TMPZIP=$(mktemp)
        curl -fsSL "https://github.com/aurine/aurine-ai/archive/refs/heads/main.zip" -o "$TMPZIP"
        mkdir -p "$AURINE_DIR"
        unzip -q "$TMPZIP" -d /tmp
        cp -r /tmp/aurine-ai-main/* "$AURINE_DIR/"
        rm -rf /tmp/aurine-ai-main "$TMPZIP"
    fi
fi

cd "$AURINE_DIR"

# Create venv
if [ ! -f ".venv/bin/python" ]; then
    echo "  Setting up virtual environment..."
    python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip > /dev/null 2>&1
    .venv/bin/python -m pip install -r requirements.txt
fi

# Setup env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        echo "AI_PROVIDER=aurine" > .env
    fi
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    echo "  Pulling AI models (first time only)..."
    ollama pull qwen2.5-coder:7b 2>/dev/null || true
    ollama pull nomic-embed-text 2>/dev/null || true
fi

# Create alias
ALIAS_LINE="alias aurine='cd $AURINE_DIR && .venv/bin/python -m app'"
if ! grep -q "alias aurine=" ~/.bashrc 2>/dev/null && ! grep -q "alias aurine=" ~/.zshrc 2>/dev/null; then
    echo "$ALIAS_LINE" >> ~/.bashrc 2>/dev/null || echo "$ALIAS_LINE" >> ~/.zshrc 2>/dev/null || true
fi

echo ""
echo "  ============================================"
echo "    Install Complete!"
echo "  ============================================"
echo ""
echo "  Start Aurine:"
echo "    cd $AURINE_DIR && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  Or add to your shell:"
echo "    $ALIAS_LINE"
echo "    aurine run"
echo ""
echo "  Open browser: http://localhost:8000"
echo "  Mobile: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-ip'):8000"
echo ""
echo "  Commands:"
echo "    aurine run           Start web server"
echo "    aurine run -p 3000   Custom port"
echo "    aurine run --network Mobile access"
echo "    aurine cli           Terminal AI agent"
echo "    aurine stop          Stop server"
echo ""

read -p "Start Aurine now? (y/n) " start
if [ "$start" = "y" ] || [ "$start" = "Y" ]; then
    .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
