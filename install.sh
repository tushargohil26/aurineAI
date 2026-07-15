#!/bin/bash
# AuraCode One-Line Installer
# Run: curl -fsSL https://raw.githubusercontent.com/tushargohil26/aurineAI/main/install.sh | bash
set -e

echo ""
echo "  AuraCode Installer"
echo "  ================="
echo ""

REPO="https://github.com/tushargohil26/aurineAI.git"
INSTALL_DIR="$HOME/aurine-ai-assistant"
AURACODE_DIR="$HOME/.auracode"

# Step 1: Check Python
echo "  [1/5] Checking Python..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1)
        if [[ "$ver" == *"Python 3"* ]]; then
            PYTHON="$cmd"
            echo "        Found: $ver"
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "        Python 3 not found!"
    echo "        Install: sudo apt install python3 python3-venv (Ubuntu)"
    echo "                 brew install python (macOS)"
    exit 1
fi

# Step 2: Check Git
echo "  [2/5] Checking Git..."
if ! command -v git &>/dev/null; then
    echo "        Git not found!"
    echo "        Install: sudo apt install git (Ubuntu)"
    exit 1
fi
echo "        Found: $(git --version)"

# Step 3: Clone or update
echo "  [3/5] Getting Aurine AI..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "        Updating..."
    cd "$INSTALL_DIR" && git pull origin main >/dev/null 2>&1
else
    echo "        Cloning..."
    git clone "$REPO" "$INSTALL_DIR" 2>/dev/null
fi
cd "$INSTALL_DIR"

# Step 4: Setup venv
echo "  [4/5] Installing dependencies..."
if [ ! -d ".venv" ]; then
    "$PYTHON" -m venv .venv 2>/dev/null
fi
source .venv/bin/activate 2>/dev/null
pip install --upgrade pip -q 2>/dev/null
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q 2>/dev/null
fi
echo "        Done"

# Step 5: Install auracode command
echo "  [5/5] Installing 'auracode' command..."
mkdir -p "$AURACODE_DIR"

# Create launcher script
cat > "$AURACODE_DIR/auracode" << LAUNCHER
#!/bin/bash
cd "$INSTALL_DIR"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python auracode.py
elif [ -f ".venv/Scripts/python.exe" ]; then
    .venv/Scripts/python.exe auracode.py
else
    echo "[AuraCode] Setup incomplete. Run installer again."
    exit 1
fi
LAUNCHER
chmod +x "$AURACODE_DIR/auracode"

# Add to PATH
if [[ ":$PATH:" != *":$AURACODE_DIR:"* ]]; then
    echo "export PATH=\"\$PATH:$AURACODE_DIR\"" >> "$HOME/.bashrc"
    echo "export PATH=\"\$PATH:$AURACODE_DIR\"" >> "$HOME/.zshrc" 2>/dev/null
    export PATH="$PATH:$AURACODE_DIR"
fi

echo "        Done"

echo ""
echo "  ========================================"
echo "  AuraCode installed successfully!"
echo "  ========================================"
echo ""
echo "  Installed to: $INSTALL_DIR"
echo "  Command:      auracode"
echo ""
echo "  To use:"
echo "    1. Close this terminal"
echo "    2. Open a NEW terminal"
echo "    3. Type: auracode"
echo ""
