#!/bin/bash
# AuraCode Installer
# Run: curl -fsSL https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.sh | bash
set -e
INSTALL_DIR="$HOME/.aurine"
BIN_DIR="$HOME/.aurine/bin"

echo ""
echo "  AuraCode Installer"
echo ""

# Check Python
PYTHON=""
for c in python3 python; do
    if command -v "$c" &>/dev/null; then
        v=$("$c" --version 2>&1)
        if [[ "$v" == *"Python 3"* ]]; then PYTHON="$c"; break; fi
    fi
done
if [ -z "$PYTHON" ]; then echo "  Python 3 not found"; exit 1; fi
echo "  [1/4] Python OK"

# Check Git
if ! command -v git &>/dev/null; then echo "  Git not found"; exit 1; fi
echo "  [2/4] Git OK"

# Clone
echo "  [3/4] Downloading..."
if [ -d "$INSTALL_DIR/.git" ]; then cd "$INSTALL_DIR" && git pull -q 2>/dev/null; else git clone https://github.com/tushargohil26/aurineAI.git "$INSTALL_DIR" 2>/dev/null; fi
cd "$INSTALL_DIR"
if [ ! -d ".venv" ]; then "$PYTHON" -m venv .venv 2>/dev/null; fi
.venv/bin/pip install -r requirements.txt -q 2>/dev/null
echo "  Done"

# Install command
echo "  [4/4] Installing auracode..."
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/auracode" << 'EOF'
#!/bin/bash
cd "$HOME/.aurine"
if [ -f ".venv/bin/python" ]; then .venv/bin/python auracode.py
elif [ -f ".venv/Scripts/python.exe" ]; then .venv/Scripts/python.exe auracode.py
else echo "[AuraCode] Not installed"; exit 1; fi
EOF
chmod +x "$BIN_DIR/auracode"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.bashrc"
    echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.zshrc" 2>/dev/null
    export PATH="$PATH:$BIN_DIR"
fi
echo "  Done"

echo ""
echo "  Installed! Open a NEW terminal and type:"
echo "    auracode"
echo ""
