import json
import os
import shutil
import subprocess
import sys
import threading
import time
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

PLUGINS = [
    {"id": "git", "name": "Git", "actions": ["status", "log", "diff", "commit", "push", "pull"]},
    {"id": "github", "name": "GitHub CLI", "actions": ["auth", "repos", "issues", "prs"]},
    {"id": "web", "name": "Web Search", "actions": ["search", "fetch", "news"]},
    {"id": "files", "name": "File Manager", "actions": ["list", "read", "write", "search"]},
    {"id": "terminal", "name": "Terminal", "actions": ["run", "processes", "env"]},
    {"id": "code", "name": "Code Runner", "actions": ["python", "javascript", "shell"]},
    {"id": "media", "name": "Media", "actions": ["pdf", "image", "video"]},
    {"id": "data", "name": "Data", "actions": ["csv", "json", "chart"]},
    {"id": "vscode", "name": "VS Code", "actions": ["open", "extensions"]},
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


def _w():
    try: return shutil.get_terminal_size().columns
    except: return 80

def _box(t, w=None):
    w = w or _w(); inn = w - 4
    if len(t) > inn: t = t[:inn-3] + "..."
    return f"  {C.GRY}\u2502{C.R} {t}{' '*(inn-len(t))} {C.GRY}\u2502{C.R}"

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
        print(_box(f"  {C.CYN}/help{C.R}                {C.D}show this help{C.R}"))
        print(_box(f"  {C.CYN}/agents{C.R}              {C.D}list available agents{C.R}"))
        print(_box(f"  {C.CYN}/agent{C.R}  <name>       {C.D}switch agent{C.R}"))
        print(_box(f"  {C.CYN}/plugins{C.R}             {C.D}list plugins{C.R}"))
        print(_box(f"  {C.CYN}/skills{C.R}              {C.D}list skills{C.R}"))
        print(_sep())
        print(_box(f"  {C.CYN}/files{C.R}  [path]       {C.D}list files{C.R}"))
        print(_box(f"  {C.CYN}/read{C.R}   <path>       {C.D}read file{C.R}"))
        print(_box(f"  {C.CYN}/run{C.R}    <command>    {C.D}run command{C.R}"))
        print(_sep())
        print(_box(f"  {C.CYN}/sessions{C.R}            {C.D}past chats{C.R}"))
        print(_box(f"  {C.CYN}/device{C.R}              {C.D}device info{C.R}"))
        print(_box(f"  {C.CYN}/model{C.R}               {C.D}current model{C.R}"))
        print(_box(f"  {C.CYN}/clear{C.R}               {C.D}clear screen{C.R}"))
        print(_box(f"  {C.CYN}/quit{C.R}                {C.D}exit{C.R}"))
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

    if cmd == "plugins":
        print()
        print(_top())
        print(_box(f"{C.B}{C.WHT}Plugins{C.R}  {C.D}({len(PLUGINS)} available){C.R}"))
        print(_sep())
        for p in PLUGINS:
            acts = ", ".join(p["actions"][:4])
            print(_box(f"  {C.CYN}{p['id'].ljust(12)}{C.R} {C.GRN}\u2713{C.R} {C.D}{acts}{C.R}"))
        print(_bot())
        print()
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

    if cmd == "sessions":
        if _HAS_AI:
            chats = get_all_chats()
            if chats:
                print()
                print(_top())
                print(_box(f"{C.B}{C.WHT}Sessions{C.R}  {C.D}({len(chats)}){C.R}"))
                print(_sep())
                for c in chats[:10]:
                    print(_box(f"  {C.D}{c['chat_id'][:16]}{C.R}  {c['last_message'][:40]}"))
                print(_bot())
                print()
            else:
                print(f"  {C.D}No sessions.{C.R}")
        return True

    if cmd == "device":
        info = {"workspace": str(WORKSPACE)}
        if _HAS_AI:
            info["device"] = get_device_name()
            info["device_id"] = get_device_id()[:16]
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
        prov = os.getenv("AI_PROVIDER", "openai")
        model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        print(f"\n  {C.D}Provider:{C.R} {C.B}{prov}{C.R}")
        print(f"  {C.D}Model:{C.R} {model}\n")
        return True

    print(f"  {C.D}Unknown command. /help{C.R}")
    return True


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
    print()
    print(_top())
    print(_box(f"{C.B}{C.CYN}AuraCode{C.R}  {C.D}v1.0{C.R}"))
    print(_box(f"{C.D}AI coding agent for your terminal{C.R}"))
    print(_sep())
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
