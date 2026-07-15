#!/bin/bash
set -e

echo ""
echo "  ============================================"
echo "    Aurine AI Assistant - One-Command Setup"
echo "  ============================================"
echo ""

cd "$(dirname "$0")"

echo "[1/5] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed."
    echo "Install with: sudo apt install python3 python3-venv"
    exit 1
fi
PYVER=$(python3 --version 2>&1)
echo "  Found: $PYVER"

echo ""
echo "[2/5] Creating virtual environment..."
if [ ! -f ".venv/bin/python" ]; then
    python3 -m venv .venv
    echo "  Virtual environment created."
else
    echo "  Virtual environment already exists."
fi

echo ""
echo "[3/5] Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip > /dev/null 2>&1
.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "[4/5] Setting up configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
    else
        echo "AI_PROVIDER=aurine" > .env
        echo "  Created default .env"
    fi
else
    echo "  .env already exists."
fi

echo ""
echo "[5/5] Checking Ollama (for local AI)..."
if command -v ollama &> /dev/null; then
    echo "  Ollama found. Starting model pull..."
    ollama pull qwen2.5-coder:7b > /dev/null 2>&1 || true
    ollama pull nomic-embed-text > /dev/null 2>&1 || true
    echo "  Models ready."
else
    echo "  Ollama not found. You can:"
    echo "    1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh"
    echo "    2. Or use a cloud API key (Groq, OpenAI, Google, etc.)"
    echo "    Set AI_PROVIDER and API key in .env file."
fi

echo ""
echo "  ============================================"
echo "    Setup Complete!"
echo "  ============================================"
echo ""
echo "  To start Aurine:"
echo "    chmod +x start.sh && ./start.sh"
echo "  Or: .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "  Open browser: http://localhost:8000"
echo "  Mobile: http://<your-ip>:8000"
echo ""
