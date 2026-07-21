#!/bin/bash
# AuraCode v2.2 - One-Line Installer
# Run: curl -fsSL https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.sh | bash

set -e
INSTALL_DIR="$HOME/.aurine"
BIN_DIR="$INSTALL_DIR/bin"
REPO_URL="https://github.com/tushargohil26/aurineAI"

echo ""
echo "  ============================================"
echo "    AuraCode v2.2 - AI Terminal Agent"
echo "    No Ollama | Free Google AI"
echo "  ============================================"
echo ""

# =========================================================================
# STEP 1: Check Python
# =========================================================================
echo "  [1/5] Checking Python..."
PYTHON=""
for c in python3 python python3.12 python3.11 python3.10; do
    if command -v "$c" &>/dev/null; then
        v=$("$c" --version 2>&1)
        if [[ "$v" == *"Python 3"* ]]; then
            minor=$(echo "$v" | cut -d. -f2)
            if [ "$minor" -ge 10 ]; then PYTHON="$c"; break; fi
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  Python 3.10+ not found."
    echo "  Install it: https://python.org or use your package manager"
    echo "    Ubuntu: sudo apt install python3 python3-venv"
    echo "    Mac: brew install python@3.12"
    exit 1
fi
echo "  [OK] Python found"

# =========================================================================
# STEP 2: Download AuraCode
# =========================================================================
echo "  [2/5] Downloading AuraCode..."

ZIP_URL="$REPO_URL/archive/refs/heads/main.zip"
ZIP_FILE="/tmp/auracode_download.zip"
EXTRACT_DIR="/tmp/auracode_extract"

curl -fsSL "$ZIP_URL" -o "$ZIP_FILE" 2>/dev/null || wget -q "$ZIP_URL" -O "$ZIP_FILE"

rm -rf "$EXTRACT_DIR"
unzip -q "$ZIP_FILE" -d "$EXTRACT_DIR" 2>/dev/null
SRC_DIR=$(find "$EXTRACT_DIR" -maxdepth 1 -type d | head -1)

# Clean install dir
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/app" "$INSTALL_DIR/.auracode/sessions" "$BIN_DIR"

# Copy essential files
cp "$SRC_DIR/auracode.py" "$INSTALL_DIR/auracode.py"

for f in __init__.py __main__.py llm.py config.py device.py memory.py agents.py agent_tools.py artifacts.py codegen.py rag.py reasoning.py cli.py main.py; do
    [ -f "$SRC_DIR/app/$f" ] && cp "$SRC_DIR/app/$f" "$INSTALL_DIR/app/$f"
done

for f in .env.example requirements.txt; do
    [ -f "$SRC_DIR/$f" ] && cp "$SRC_DIR/$f" "$INSTALL_DIR/$f"
done

# Create .env if not present
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > "$INSTALL_DIR/.env" << 'ENVEOF'
AI_PROVIDER=google
GOOGLE_API_KEY=
GOOGLE_CHAT_MODEL=gemini-2.0-flash
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
GROQ_API_KEY=
DEEPSEEK_API_KEY=
ENVEOF
fi

rm -f "$ZIP_FILE"
rm -rf "$EXTRACT_DIR"
echo "  [OK] Downloaded"

# =========================================================================
# STEP 3: Create venv + install dependencies
# =========================================================================
echo "  [3/5] Installing dependencies..."

VENV_DIR="$INSTALL_DIR/.venv"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    "$PYTHON" -m venv "$VENV_DIR" 2>/dev/null
fi

"$VENV_DIR/bin/pip" install --upgrade pip -q 2>/dev/null
"$VENV_DIR/bin/pip" install openai httpx pydantic python-dotenv rich questionary pygments tiktoken numpy scikit-learn -q 2>/dev/null || \
"$VENV_DIR/bin/pip" install openai httpx pydantic python-dotenv rich questionary pygments tiktoken numpy scikit-learn

echo "  [OK] Dependencies installed"

# =========================================================================
# STEP 4: Create global 'auracode' command
# =========================================================================
echo "  [4/5] Creating 'auracode' command..."

cat > "$BIN_DIR/auracode" << LAUNCHER
#!/bin/bash
cd "$INSTALL_DIR"

# Auto-update
if [ -d ".git" ]; then
    BEFORE=\$(git rev-parse HEAD 2>/dev/null)
    git pull origin main --quiet 2>/dev/null
    AFTER=\$(git rev-parse HEAD 2>/dev/null)
    if [ "\$BEFORE" != "\$AFTER" ]; then
        echo "  Updated! Restarting..."
        sleep 1
    fi
fi

# Ensure sessions dir
mkdir -p ".auracode/sessions"

# Launch
"$VENV_DIR/bin/python" auracode.py
LAUNCHER
chmod +x "$BIN_DIR/auracode"

# Add to PATH
add_to_path() {
    local file="$1"
    if [ -f "$file" ] && ! grep -q "$BIN_DIR" "$file" 2>/dev/null; then
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$file"
    fi
}
add_to_path "$HOME/.bashrc"
add_to_path "$HOME/.zshrc"
add_to_path "$HOME/.profile"
export PATH="$PATH:$BIN_DIR"

echo "  [OK] 'auracode' command ready"

# =========================================================================
# STEP 5: Verify
# =========================================================================
echo "  [5/5] Verifying..."

if [ -f "$BIN_DIR/auracode" ]; then
    echo "  [OK] auracode command ready"
else
    echo "  [!] May need manual setup"
fi

# =========================================================================
# DONE
# =========================================================================
echo ""
echo "  ============================================"
echo "    AuraCode v2.2 Installed!"
echo "  ============================================"
echo ""
echo "  Setup:"
echo "    1. Get free API key: https://aistudio.google.com/app/apikey"
echo "    2. Edit: $INSTALL_DIR/.env"
echo "    3. Add: GOOGLE_API_KEY=your_key"
echo ""
echo "  Usage:"
echo "    Open NEW terminal and type: auracode"
echo ""
echo "  Commands:"
echo "    Ctrl+P   Command Palette"
echo "    /help    Show all commands"
echo ""
