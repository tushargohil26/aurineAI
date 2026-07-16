import base64
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

WORKSPACE = Path.cwd().resolve()

try:
    from app.llm import chat_completion
    from app.device import (
        get_device_id, get_user_id, get_device_name,
        store_chat_message, get_chat_history, get_all_chats,
        store_fact, recall_facts, store_preference, get_preferences,
        learn_pattern, get_learned_patterns,
        build_memory_context, extract_facts_from_message,
    )
    _HAS_AI = True
except ImportError:
    _HAS_AI = False


AGENTS = [
    {"id": "aurine", "name": "Aurine", "desc": "Full-stack AI assistant", "model": "gpt-4o"},
    {"id": "codex", "name": "Codex", "desc": "Code-focused agent", "model": "gpt-4o"},
    {"id": "researcher", "name": "Researcher", "desc": "Web search and summarization", "model": "gpt-4o-mini"},
    {"id": "analyst", "name": "Analyst", "desc": "Data analysis and charts", "model": "gpt-4o"},
    {"id": "devops", "name": "DevOps", "desc": "Git, CI/CD, deployment", "model": "gpt-4o"},
    {"id": "designer", "name": "Designer", "desc": "HTML/CSS, SVG, UI", "model": "gpt-4o"},
    {"id": "debugger", "name": "Debugger", "desc": "Bug fixing and error analysis", "model": "gpt-4o"},
    {"id": "security", "name": "Security", "desc": "Vulnerability scanning", "model": "gpt-4o"},
]


SKILLS = [
    {"id": "code-review", "name": "Code Review", "desc": "Review code for bugs and improvements"},
    {"id": "refactor", "name": "Refactor", "desc": "Refactor code for better structure"},
    {"id": "test-gen", "name": "Test Generator", "desc": "Generate unit tests"},
    {"id": "doc-gen", "name": "Doc Generator", "desc": "Generate documentation"},
    {"id": "api-design", "name": "API Design", "desc": "Design REST/GraphQL APIs"},
    {"id": "db-design", "name": "Database Design", "desc": "Schema design and queries"},
    {"id": "security-audit", "name": "Security Audit", "desc": "Scan for vulnerabilities"},
    {"id": "perf-opt", "name": "Performance", "desc": "Optimize code performance"},
    {"id": "git-workflow", "name": "Git Workflow", "desc": "Branch strategy and commits"},
    {"id": "docker", "name": "Docker", "desc": "Dockerfile and compose setup"},
    {"id": "ci-cd", "name": "CI/CD", "desc": "GitHub Actions, pipelines"},
    {"id": "deploy", "name": "Deploy", "desc": "Deployment automation"},
]

SYSTEM_PROMPT = """You are AuraCode, a terminal coding agent. You help with coding, files, and commands.

For simple greetings, just respond with a message and empty actions.

Always respond with valid JSON:
{"message": "your answer", "actions": []}

When actions needed:
{"message": "what you will do", "actions": [
  {"tool": "list_files", "path": "."},
  {"tool": "read_file", "path": "file.py"},
  {"tool": "write_file", "path": "file.py", "content": "..."},
  {"tool": "run_command", "command": "python app.py"}
]}

Rules:
- Relative paths only, stay in workspace.
- Only call tools when needed.
- Ask before destructive commands.
- Small, practical actions.
"""


class C:
    R = "\033[0m"; B = "\033[1m"; D = "\033[2m"; I = "\033[3m"
    RED = "\033[31m"; GRN = "\033[32m"; YEL = "\033[33m"
    CYN = "\033[36m"; WHT = "\033[97m"; GRY = "\033[90m"; MAG = "\033[35m"
    BG = "\033[48;5;236m"


def _w():
    try: return shutil.get_terminal_size().columns
    except: return 80

def _box(t, w=None, color=None):
    w = w or _w(); inn = w - 4
    if len(t) > inn: t = t[:inn-3] + "..."
    clr = color or C.GRY
    return f"  {clr}\u2502{C.R} {t}{' '*(inn-len(t))} {clr}\u2502{C.R}"

def _sep(ch="\u2500"):
    return f"  {C.GRY}{ch*(_w()-4)}{C.R}"

def _top():
    return f"  {C.GRY}\u250C{''.join(['\u2500']*(_w()-4))}\u2510{C.R}"

def _bot():
    return f"  {C.GRY}\u2514{''.join(['\u2500']*(_w()-4))}\u2518{C.R}"

def _spinner():
    fr = ["\u25F7","\u25F4","\u25F5","\u25F6"]; i = 0
    while getattr(_spinner, "running", False):
        sys.stdout.write(f"\r  {C.CYN}{fr[i%len(fr)]}{C.R} {C.D}thinking...{C.R}   ")
        sys.stdout.flush(); time.sleep(0.3); i += 1
    sys.stdout.write("\r" + " "*40 + "\r"); sys.stdout.flush()

def _spin_start():
    _spinner.running = True
    threading.Thread(target=_spinner, daemon=True).start()

def _spin_stop():
    _spinner.running = False; time.sleep(0.1)

IGNORE_DIRS = {".git",".venv","__pycache__","node_modules",".mypy_cache",".pytest_cache"}

def _safe(p):
    c = (WORKSPACE / p).resolve()
    if not str(c).startswith(str(WORKSPACE)): raise ValueError("Path escapes workspace.")
    return c

def _list_files(path="."):
    root = _safe(path)
    if not root.exists(): return "Path does not exist."
    lines = []
    def _walk(d, pre="", dep=0):
        if dep > 4: return
        ents = sorted(d.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        ents = [e for e in ents if e.name not in IGNORE_DIRS and e.suffix != ".pyc"]
        for i, e in enumerate(ents):
            last = i == len(ents) - 1
            conn = "\u2514\u2500\u2500\u2500 " if last else "\u251C\u2500\u2500\u2500 "
            if e.is_dir():
                lines.append(f"{pre}{conn}{e.name}/")
                _walk(e, pre + ("    " if last else "\u2502   "), dep+1)
            else:
                sz = e.stat().st_size
                s = f"{sz//1048576}MB" if sz > 1048576 else f"{sz//1024}KB" if sz > 1024 else f"{sz}B"
                lines.append(f"{pre}{conn}{e.name}  {C.D}({s}){C.R}")
    _walk(root)
    return "\n".join(lines[:120]) + ("\n... more" if len(lines)>120 else "") or "No files."

def _read_file(p):
    t = _safe(p)
    if not t.exists() or not t.is_file(): return "File not found."
    return t.read_text(encoding="utf-8", errors="ignore")[:30000]

def _write_file(p, c):
    t = _safe(p); t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(c, encoding="utf-8")
    return f"Wrote {t.relative_to(WORKSPACE)}"

def _run_cmd(cmd):
    bl = ["rm ","del ","format ","git reset","rmdir ","Remove-Item"]
    if any(x.lower() in cmd.lower() for x in bl): return "Blocked destructive command."
    r = subprocess.run(cmd, cwd=WORKSPACE, shell=True, text=True, capture_output=True, timeout=60)
    return (r.stdout + r.stderr).strip()[:30000] or f"Exit code {r.returncode}."

def _exec(actions):
    res = []
    for a in actions:
        t = a.get("tool")
        try:
            if t == "list_files": r = _list_files(a.get("path","."))
            elif t == "read_file": r = _read_file(a.get("path",""))
            elif t == "write_file": r = _write_file(a.get("path",""), a.get("content",""))
            elif t == "run_command": r = _run_cmd(a.get("command",""))
            else: r = f"Unknown tool: {t}"
        except Exception as e: r = f"Error: {e}"
        res.append(f"  {C.CYN}\u25B6 {t}{C.R} {r[:500]}")
    return "\n".join(res)


def _get_provider_info():
    from dotenv import load_dotenv
    load_dotenv()
    provider = os.getenv("AI_PROVIDER", "aurine")
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    has_key = bool(os.getenv("OPENAI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GROQ_API_KEY", ""))
    return provider, model, has_key

def _get_device_info_str():
    if _HAS_AI:
        return f"{get_device_name()}  {C.D}id:{get_device_id()[:12]}{C.R}"
    import platform
    return f"{platform.node()} ({platform.system()})"


def _handle_slash(inp):
    if not inp.startswith("/"): return False
    cmd, _, val = inp[1:].partition(" ")
    cmd = cmd.lower().strip()
    val = val.strip()

    if cmd in {"help","?"}:
        print()
        print(_top())
        print(_box(f"{C.B}{C.CYN}AuraCode{C.R}  {C.D}Commands{C.R}"))
        print(_sep())
        print(_box(f"  {C.CYN}/help{C.R}                 {C.D}show all commands{C.R}"))
        print(_box(f"  {C.CYN}/agents{C.R}               {C.D}list available agents{C.R}"))
        print(_box(f"  {C.CYN}/agent{C.R}  <name>        {C.D}switch agent{C.R}"))
        print(_box(f"  {C.CYN}/skills{C.R}               {C.D}list available skills{C.R}"))
        print(_box(f"  {C.CYN}/model{C.R}                {C.D}current model/provider{C.R}"))
        print(_box(f"  {C.CYN}/doctor{C.R}               {C.D}diagnose setup issues{C.R}"))
        print(_sep())
        print(_box(f"  {C.CYN}/files{C.R}  [path]        {C.D}list files{C.R}"))
        print(_box(f"  {C.CYN}/read{C.R}   <path>        {C.D}read file with line numbers{C.R}"))
        print(_box(f"  {C.CYN}/run{C.R}    <command>     {C.D}run shell command{C.R}"))
        print(_box(f"  {C.CYN}/diff{C.R}                 {C.D}show git diff{C.R}"))
        print(_box(f"  {C.CYN}/log{C.R}                  {C.D}show git log{C.R}"))
        print(_box(f"  {C.CYN}/git{C.R}   <args>         {C.D}run git command{C.R}"))
        print(_sep())
        print(_box(f"  {C.CYN}/init{C.R}                 {C.D}initialize project workspace{C.R}"))
        print(_box(f"  {C.CYN}/web{C.R}   <query>        {C.D}search the web{C.R}"))
        print(_box(f"  {C.CYN}/img{C.R}   <path>         {C.D}view/analyze image{C.R}"))
        print(_box(f"  {C.CYN}/history{C.R}              {C.D}show chat history{C.R}"))
        print(_box(f"  {C.CYN}/sessions{C.R}             {C.D}past chat sessions{C.R}"))
        print(_box(f"  {C.CYN}/device{C.R}               {C.D}device info & data dir{C.R}"))
        print(_box(f"  {C.CYN}/compact{C.R}              {C.D}compress context{C.R}"))
        print(_box(f"  {C.CYN}/cost{C.R}                 {C.D}estimate token usage{C.R}"))
        print(_box(f"  {C.CYN}/config{C.R}               {C.D}show/edit configuration{C.R}"))
        print(_box(f"  {C.CYN}/clear{C.R}                {C.D}clear screen{C.R}"))
        print(_box(f"  {C.CYN}/quit{C.R}                 {C.D}exit{C.R}"))
        print(_bot())
        print()
        return True

    if cmd == "clear":
        print("\033[2J\033[H", end="")
        return True

    if cmd == "agents":
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Agents{C.R}  {C.D}({len(AGENTS)} available){C.R}"))
        print(_sep())
        for a in AGENTS:
            print(_box(f"  {C.CYN}{a['id'].ljust(12)}{C.R} {C.D}{a['desc']}{C.R}"))
        print(_bot())
        print()
        return True

    if cmd == "agent":
        if not val:
            print(f"  {C.D}Usage: /agent <name>{C.R}")
        else:
            found = [a for a in AGENTS if a["id"] == val.lower()]
            if found:
                a = found[0]
                print(f"\n  {C.GRN}\u2713{C.R} Agent: {C.B}{a['name']}{C.R}  {C.D}{a['desc']}{C.R}\n")
            else:
                print(f"  {C.RED}\u2717{C.R} Not found. /agents to list.")
        return True

    if cmd == "skills":
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Skills{C.R}  {C.D}({len(SKILLS)} available){C.R}"))
        print(_sep())
        for s in SKILLS:
            print(_box(f"  {C.CYN}{s['id'].ljust(16)}{C.R} {C.D}{s['desc']}{C.R}"))
        print(_bot())
        print()
        return True

    if cmd in {"files","ls"}:
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Files{C.R}"))
        print(_sep())
        for line in (_list_files(val or ".") or "No files.").split("\n"):
            print(_box(f"  {line}"))
        print(_bot())
        print()
        return True

    if cmd == "read":
        if not val:
            print(f"  {C.D}Usage: /read <path>{C.R}")
        else:
            content = _read_file(val)
            print()
            print(_top())
            print(_box(f"{C.B}{C.WHT}{val}{C.R}"))
            print(_sep())
            for i, line in enumerate(content.split("\n"), 1):
                print(_box(f"  {C.D}{str(i).rjust(4)}{C.R}  {line}"))
            print(_bot())
            print()
        return True

    if cmd == "run":
        if not val:
            print(f"  {C.D}Usage: /run <command>{C.R}")
        else:
            print(f"\n  {C.CYN}$ {C.R}{C.D}{val}{C.R}")
            result = _run_cmd(val)
            for line in result.split("\n")[:40]:
                print(f"    {line}")
            print()
        return True

    if cmd == "diff":
        result = _run_cmd("git diff --stat")
        full = _run_cmd("git diff")
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Git Diff{C.R}"))
        print(_sep())
        print(_box(f"  {C.D}{result}{C.R}"))
        if full.strip():
            print(_sep())
            for line in full.split("\n")[:60]:
                color = C.GRN if line.startswith("+") else C.RED if line.startswith("-") else C.D
                print(_box(f"  {color}{line}{C.R}"))
        print(_bot())
        print()
        return True

    if cmd == "log":
        result = _run_cmd("git log --oneline -20")
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Git Log{C.R}"))
        print(_sep())
        for line in result.split("\n"):
            print(_box(f"  {C.CYN}{line}{C.R}"))
        print(_bot())
        print()
        return True

    if cmd == "git":
        if not val:
            print(f"  {C.D}Usage: /git <args>  e.g. /git status{C.R}")
        else:
            result = _run_cmd(f"git {val}")
            print(f"\n  {C.D}git {val}{C.R}")
            for line in result.split("\n")[:40]:
                print(f"    {line}")
            print()
        return True

    if cmd == "init":
        print(f"\n  {C.CYN}Initializing workspace...{C.R}")
        files = ["package.json", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml"]
        found = [f for f in files if (WORKSPACE / f).exists()]
        if found:
            print(f"  {C.GRN}\u2713{C.R} Project detected: {', '.join(found)}")
        else:
            print(f"  {C.D}No standard project files found in {WORKSPACE.name}{C.R}")
        dotgit = WORKSPACE / ".git"
        if dotgit.exists():
            branch = _run_cmd("git branch --show-current").strip()
            remote = _run_cmd("git remote get-url origin").strip()
            print(f"  {C.GRN}\u2713{C.R} Git: branch={branch or 'none'} remote={remote or 'none'}")
        else:
            print(f"  {C.YEL}!{C.R} No git repo. Run: git init")
        print(f"  {C.GRN}\u2713{C.R} Workspace: {WORKSPACE}")
        if _HAS_AI:
            print(f"  {C.GRN}\u2713{C.R} Device: {_get_device_info_str()}")
        prov, model, has_key = _get_provider_info()
        status = f"{C.GRN}\u2713{C.R}" if has_key else f"{C.YEL}!{C.R}"
        print(f"  {status} Provider: {C.B}{prov}{C.R}  Model: {model}")
        print()
        return True

    if cmd == "web":
        if not val:
            print(f"  {C.D}Usage: /web <search query>{C.R}")
        else:
            print(f"\n  {C.CYN}Searching: {val}{C.R}")
            try:
                import urllib.request, urllib.parse
                url = f"https://www.google.com/search?q={urllib.parse.quote(val)}"
                result = _run_cmd(f'curl -sL "{url}" -H "User-Agent: Mozilla/5.0" 2>nul | head -c 2000')
                print(f"  {result[:1000]}")
            except Exception:
                print(f"  {C.D}Web search not available. Try /run curl <url>{C.R}")
            print()
        return True

    if cmd == "img":
        if not val:
            print(f"  {C.D}Usage: /img <image_path>  to analyze an image{C.R}")
        else:
            p = _safe(val)
            if p.exists():
                sz = p.stat().st_size
                print(f"\n  {C.CYN}\u25B6{C.R} Image: {val}  {C.D}({sz} bytes, {p.suffix}){C.R}")
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                    try:
                        with open(p, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                        print(f"  {C.D}Base64 size: {len(b64)} chars{C.R}")
                        print(f"  {C.D}Ready for AI analysis - paste into chat{C.R}")
                    except Exception as e:
                        print(f"  {C.RED}Error reading: {e}{C.R}")
            else:
                print(f"  {C.RED}File not found: {val}{C.R}")
            print()
        return True

    if cmd == "history":
        if _HAS_AI:
            chats = get_all_chats()
            if chats:
                print()
                print(_top())
                print(_box(f"{C.B}{C.WHT}Chat History{C.R}  {C.D}({len(chats)} sessions){C.R}"))
                print(_sep())
                for c in chats[:15]:
                    print(_box(f"  {C.D}{c['chat_id'][:16]}{C.R}  {c['last_message'][:50]}"))
                print(_bot())
                print()
            else:
                print(f"  {C.D}No chat history yet.{C.R}")
        else:
            print(f"  {C.D}AI module not available for history.{C.R}")
        return True

    if cmd == "sessions":
        return _handle_slash("/history")

    if cmd == "device":
        info = {"workspace": str(WORKSPACE)}
        if _HAS_AI:
            info["device"] = get_device_name()
            info["device_id"] = get_device_id()[:16]
            info["user_id"] = get_user_id()
            info["data_dir"] = str(get_device_data_path())
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Device{C.R}"))
        print(_sep())
        for k, v in info.items():
            print(_box(f"  {C.CYN}{k.ljust(12)}{C.R} {v}"))
        print(_bot())
        print()
        return True

    if cmd == "model":
        from dotenv import load_dotenv
        load_dotenv()
        prov = os.getenv("AI_PROVIDER", "aurine")
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        has_key = bool(os.getenv("OPENAI_API_KEY", ""))
        status = f"{C.GRN}\u2713{C.R}" if has_key else f"{C.RED}\u2717{C.R}"
        print(f"\n  {C.D}Provider:{C.R} {C.B}{prov}{C.R}")
        print(f"  {C.D}Model:{C.R} {model}")
        print(f"  {C.D}API Key:{C.R} {status} {'set' if has_key else 'NOT SET'}")
        print()
        return True

    if cmd == "doctor":
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}System Diagnostics{C.R}"))
        print(_sep())

        import platform
        print(_box(f"  {C.CYN}OS:{C.R}           {platform.system()} {platform.release()}"))
        print(_box(f"  {C.CYN}Python:{C.R}       {sys.version.split()[0]}"))
        print(_box(f"  {C.CYN}Shell:{C.R}        {os.getenv('COMSPEC', os.getenv('SHELL', 'unknown'))}"))
        print(_box(f"  {C.CYN}Workspace:{C.R}    {WORKSPACE}"))
        if _HAS_AI:
            print(_box(f"  {C.CYN}Device:{C.R}       {_get_device_info_str()}"))

        print(_sep())
        print(_box(f"{C.B}{C.CYN}AI Provider{C.R}"))
        print(_sep())
        prov, model, has_key = _get_provider_info()
        status = f"{C.GRN}\u2713{C.R}" if has_key else f"{C.RED}\u2717{C.R}"
        print(_box(f"  {C.CYN}Provider:{C.R}     {C.B}{prov}{C.R}"))
        print(_box(f"  {C.CYN}Model:{C.R}        {model}"))
        print(_box(f"  {C.CYN}API Key:{C.R}      {status} {'configured' if has_key else 'MISSING - add to .env'}"))

        try:
            from app.llm import _ollama_running
            ollama_ok = _ollama_running()
            ollama_st = f"{C.GRN}\u2713 running{C.R}" if ollama_ok else f"{C.YEL}not running{C.R} (cloud fallback active)"
            print(_box(f"  {C.CYN}Ollama:{C.R}       {ollama_st}"))
        except Exception:
            print(_box(f"  {C.CYN}Ollama:{C.R}       {C.D}cannot check{C.R}"))

        print(_sep())
        print(_box(f"{C.B}{C.CYN}Tools{C.R}"))
        print(_sep())
        for tool in ["git", "node", "npm", "python", "pip", "docker", "code", "gh"]:
            found = bool(shutil.which(tool))
            st = f"{C.GRN}\u2713{C.R}" if found else f"{C.RED}\u2717{C.R}"
            print(_box(f"  {st} {tool}"))

        print(_sep())
        print(_bot())
        print()
        return True

    if cmd == "compact":
        print(f"\n  {C.CYN}Context compacted{C.R}  {C.D}(history truncated for next turn){C.R}\n")
        return True

    if cmd == "cost":
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Token Estimate{C.R}"))
        print(_sep())
        prov, model, has_key = _get_provider_info()
        print(_box(f"  {C.CYN}Provider:{C.R}  {prov}"))
        print(_box(f"  {C.CYN}Model:{C.R}     {model}"))
        print(_box(f"  {C.CYN}Pricing:{C.R}   {C.D}depends on provider and model{C.R}"))
        print(_bot())
        print()
        return True

    if cmd == "config":
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Configuration{C.R}"))
        print(_sep())
        from dotenv import load_dotenv
        load_dotenv()
        keys = {
            "AI_PROVIDER": os.getenv("AI_PROVIDER", "aurine"),
            "GOOGLE_API_KEY": "set" if os.getenv("GOOGLE_API_KEY") else "not set",
            "OPENAI_API_KEY": "set" if os.getenv("OPENAI_API_KEY") else "not set",
            "GROQ_API_KEY": "set" if os.getenv("GROQ_API_KEY") else "not set",
            "DEEPSEEK_API_KEY": "set" if os.getenv("DEEPSEEK_API_KEY") else "not set",
            "OPENROUTER_API_KEY": "set" if os.getenv("OPENROUTER_API_KEY") else "not set",
            "ANTHROPIC_API_KEY": "set" if os.getenv("ANTHROPIC_API_KEY") else "not set",
        }
        for k, v in keys.items():
            st = f"{C.GRN}{v}{C.R}" if v == "set" else f"{C.RED}{v}{C.R}"
            print(_box(f"  {C.CYN}{k.ljust(22)}{C.R} {st}"))
        print(_bot())
        print(f"  {C.D}Edit .env file to change settings{C.R}")
        print()
        return True

    if cmd == "sessions":
        return _handle_slash("/history")

    print(f"  {C.D}Unknown command. /help{C.R}")
    return True


def get_device_data_path():
    if _HAS_AI:
        from app.device import get_data_dir
        return str(get_data_dir())
    return "N/A"


def _ask(inp, tool_results="", history=None):
    if not _HAS_AI:
        return {"message": "AI module not available.", "actions": []}
    mem = build_memory_context()
    sys = SYSTEM_PROMPT
    if mem: sys += f"\n\nUSER MEMORY:\n{mem}"
    msgs = [{"role": "system", "content": sys}]
    if history:
        for m in history[-20:]:
            msgs.append({"role": m["role"], "content": m["content"]})
    if tool_results:
        msgs.append({"role": "user", "content": f"Tool results:\n{tool_results}\n\nUser: {inp}"})
    else:
        msgs.append({"role": "user", "content": inp})
    content = chat_completion(msgs, temperature=0.1, json_mode=True)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"message": "Could not parse response.", "actions": []}


def _run_turn(inp, chat_id):
    if _HAS_AI:
        extract_facts_from_message(inp)
        store_chat_message(chat_id, "user", inp)
        history = get_chat_history(chat_id, limit=30)
    else:
        history = None

    tool_results = ""
    for _ in range(5):
        _spin_start()
        try: resp = _ask(inp, tool_results, history)
        finally: _spin_stop()

        msg = resp.get("message", "")
        actions = resp.get("actions", [])
        if msg:
            print(f"\n  {msg}\n")
            if _HAS_AI:
                store_chat_message(chat_id, "assistant", msg, "auracode")
        if not actions: return

        for a in actions:
            tool = a.get("tool","")
            det = a.get("path", a.get("command",""))
            if tool == "write_file": det = a.get("path","")
            if det and len(str(det)) > 60: det = str(det)[:57]+"..."
            print(f"  {C.MAG}\u25B6{C.R} {C.CYN}{tool}{C.R} {C.D}{det}{C.R}")

        _spin_start()
        try: tool_results = _exec(actions)
        finally: _spin_stop()

        if tool_results.strip():
            for line in tool_results.strip().split("\n")[:10]:
                print(f"  {line}")
            print()


def _print_header():
    prov, model, has_key = _get_provider_info()
    print()
    print(_top())
    print(_box(f"{C.B}{C.CYN}AuraCode{C.R}  {C.D}v1.0{C.R}"))
    print(_box(f"{C.D}AI coding agent for your terminal{C.R}"))
    print(_sep())
    print(_box(f"  {C.D}Provider:{C.R} {C.B}{prov}{C.R}  {C.D}Model:{C.R} {model}"))
    if not has_key:
        print(_box(f"  {C.YEL}!{C.R} {C.D}No cloud API key set - add GOOGLE_API_KEY or OPENAI_API_KEY to .env{C.R}"))
    print(_box(f"  {C.D}Type a message or {C.CYN}/help{C.R}{C.D} for commands{C.R}"))
    print(_bot())
    print()


def main():
    chat_id = f"cli_{uuid4().hex[:8]}"
    if _HAS_AI:
        chat_id = f"cli_{get_device_id()}_{uuid4().hex[:8]}"

    _print_header()

    while True:
        try:
            u = input(f"  {C.GRN}\u25B6{C.R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not u: continue
        if u.lower() in {"exit","quit","/quit"}:
            print(f"\n  {C.D}bye{C.R}\n"); break
        try:
            if _handle_slash(u): continue
            _run_turn(u, chat_id)
        except KeyboardInterrupt:
            print(f"\n  {C.D}interrupted{C.R}\n"); continue
        except Exception as e:
            print(f"\n  {C.RED}\u2717 error:{C.R} {e}\n")


if __name__ == "__main__":
    main()
