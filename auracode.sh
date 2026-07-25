#!/bin/bash
# AuraCode v3.0 - Auto-Update Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '3\.\d+' | head -1)
        if [ -n "$ver" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  [X] Python 3.10+ required."
    echo "  Install: sudo apt install python3 python3-pip"
    exit 1
fi

# Fast startup: skip setup if already done
if [ ! -f ".venv/bin/python" ] && [ ! -f ".venv/Scripts/python.exe" ]; then
    echo "  Setting up..."
    $PYTHON -m venv .venv 2>/dev/null
fi

VENV_PY=".venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
    VENV_PY=".venv/Scripts/python.exe"
fi

if [ ! -f ".venv/.deps_installed" ]; then
    echo "  Installing packages..."
    $VENV_PY -m pip install rich questionary fastapi uvicorn pypdf openpyxl -q 2>/dev/null
    echo "ok" > ".venv/.deps_installed"
fi

# Ensure .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        cat > .env << 'ENVEOF'
AI_PROVIDER=aurine
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen2.5-coder:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
AURINE_NATIVE_MODEL=qwen2.5-coder:7b
AURINE_EMBEDDING_MODEL=nomic-embed-text
GOOGLE_API_KEY=
GOOGLE_CHAT_MODEL=gemini-2.0-flash
GROQ_API_KEY=
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
VECTOR_DB=./vector_store.sqlite3
DATA_DIR=./data
ENVEOF
    fi
fi

# Auto-update from GitHub
echo "  Checking for updates..."
$VENV_PY -c "
import urllib.request,zipfile,os,shutil,tempfile
url='https://github.com/tushargohil26/aurineAI/archive/refs/heads/main.zip'
td=tempfile.mkdtemp()
urllib.request.urlretrieve(url,os.path.join(td,'u.zip'))
zipfile.ZipFile(os.path.join(td,'u.zip')).extractall(td)
src=[d for d in os.listdir(td) if os.path.isdir(os.path.join(td,d)) and d.startswith('aurineAI')]
if src:
    for f in ['auracode.py']:
        fp=os.path.join(src[0],f)
        if os.path.exists(fp): shutil.copy2(fp,f)
    app_src=os.path.join(src[0],'app')
    if os.path.exists(app_src):
        shutil.copytree(app_src,'app',dirs_exist_ok=True)
shutil.rmtree(td,ignore_errors=True)
" 2>/dev/null

# Ensure dirs
mkdir -p ".auracode/sessions" 2>/dev/null

# Launch
$VENV_PY auracode.py
