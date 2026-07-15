import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from uuid import uuid4

from app.llm import chat_completion
from app.device import (
    get_device_id, get_user_id, get_device_name,
    store_chat_message, get_chat_history, get_all_chats,
    store_fact, recall_facts, store_preference, get_preferences,
    learn_pattern, get_learned_patterns,
    build_memory_context, extract_facts_from_message,
)

WORKSPACE = Path.cwd().resolve()

AGENTS = [
    {"id": "aurine", "name": "Aurine", "desc": "Full-stack AI assistant with plugins and code generation", "model": "gpt-4o"},
    {"id": "codex", "name": "Codex", "desc": "Code-focused agent for editing and writing code", "model": "gpt-4o"},
    {"id": "researcher", "name": "Researcher", "desc": "Web search, fetch URLs, summarize content", "model": "gpt-4o-mini"},
    {"id": "analyst", "name": "Analyst", "desc": "Data analysis, charts, statistics, JSON/CSV processing", "model": "gpt-4o"},
    {"id": "devops", "name": "DevOps", "desc": "Git, GitHub, CI/CD, terminal commands, deployment", "model": "gpt-4o"},
    {"id": "designer", "name": "Designer", "desc": "HTML/CSS generation, SVG art, UI components", "model": "gpt-4o"},
    {"id": "architect", "name": "Architect", "desc": "System design, architecture, planning", "model": "gpt-4o"},
    {"id": "debugger", "name": "Debugger", "desc": "Find and fix bugs, error analysis, stack traces", "model": "gpt-4o"},
    {"id": "documenter", "name": "Documenter", "desc": "README, API docs, code comments, wikis", "model": "gpt-4o-mini"},
    {"id": "tester", "name": "Tester", "desc": "Unit tests, integration tests, test coverage", "model": "gpt-4o"},
    {"id": "security", "name": "Security", "desc": "Vulnerability scanning, CVE review, security audit", "model": "gpt-4o"},
    {"id": "db", "name": "Database", "desc": "SQL queries, schema design, data modeling", "model": "gpt-4o"},
    {"id": "api", "name": "API", "desc": "REST/GraphQL endpoint design, OpenAPI specs", "model": "gpt-4o"},
    {"id": "mobile", "name": "Mobile", "desc": "React Native, Flutter, mobile UI patterns", "model": "gpt-4o"},
    {"id": "ml", "name": "ML Engineer", "desc": "Machine learning, data pipelines, model training", "model": "gpt-4o"},
    {"id": "writer", "name": "Writer", "desc": "Technical writing, blog posts, documentation", "model": "gpt-4o-mini"},
    {"id": "translator", "name": "Translator", "desc": "Multi-language translation and localization", "model": "gpt-4o-mini"},
    {"id": "product", "name": "Product", "desc": "PRDs, user stories, feature planning", "model": "gpt-4o-mini"},
    {"id": "devrel", "name": "DevRel", "desc": "Community content, tutorials, demos", "model": "gpt-4o-mini"},
    {"id": "perf", "name": "Performance", "desc": "Optimization, profiling, bottleneck analysis", "model": "gpt-4o"},
    {"id": "data", "name": "Data Engineer", "desc": "ETL pipelines, data warehousing, Spark/SQL", "model": "gpt-4o"},
    {"id": "cloud", "name": "Cloud", "desc": "AWS/GCP/Azure, Docker, Kubernetes, Terraform", "model": "gpt-4o"},
    {"id": "frontend", "name": "Frontend", "desc": "React, Vue, CSS, responsive design, a11y", "model": "gpt-4o"},
    {"id": "backend", "name": "Backend", "desc": "Node.js, Python, Go, APIs, databases", "model": "gpt-4o"},
    {"id": "fullstack", "name": "Fullstack", "desc": "End-to-end feature implementation", "model": "gpt-4o"},
    {"id": "cli", "name": "CLI Tools", "desc": "Command-line tools, shell scripts, automation", "model": "gpt-4o"},
    {"id": "embedded", "name": "Embedded", "desc": "Embedded systems, IoT, firmware, C/C++", "model": "gpt-4o"},
    {"id": "blockchain", "name": "Blockchain", "desc": "Smart contracts, Solidity, Web3", "model": "gpt-4o"},
    {"id": "game", "name": "Game Dev", "desc": "Unity, Unreal, game logic, shaders", "model": "gpt-4o"},
    {"id": "bio", "name": "Bio Info", "desc": "Bioinformatics, genomics, data analysis", "model": "gpt-4o"},
    {"id": "quant", "name": "Quant", "desc": "Trading algorithms, financial modeling, risk", "model": "gpt-4o"},
    {"id": "legal", "name": "Legal", "desc": "License review, compliance, contract analysis", "model": "gpt-4o-mini"},
    {"id": "hr", "name": "HR", "desc": "Job descriptions, onboarding, team processes", "model": "gpt-4o-mini"},
    {"id": "marketing", "name": "Marketing", "desc": "SEO, content strategy, campaign planning", "model": "gpt-4o-mini"},
    {"id": "support", "name": "Support", "desc": "Ticket triage, FAQ, customer communication", "model": "gpt-4o-mini"},
]

PLUGINS = [
    {"id": "git", "name": "Git", "actions": ["status", "log", "diff", "branches", "commit", "push", "pull", "clone", "stash", "tags"]},
    {"id": "github", "name": "GitHub", "actions": ["auth", "repos", "issues", "prs", "search", "create_repo", "clone"]},
    {"id": "web-search", "name": "Web Search", "actions": ["search", "fetch", "news", "docs"]},
    {"id": "code-runner", "name": "Code Runner", "actions": ["python", "javascript", "shell", "run_file"]},
    {"id": "file-manager", "name": "File Manager", "actions": ["list", "read", "write", "search", "delete", "rename", "copy", "tree"]},
    {"id": "image-gen", "name": "Image Gen", "actions": ["generate", "svg", "html_art", "thumbnails"]},
    {"id": "data-analyzer", "name": "Data Analyzer", "actions": ["analyze_csv", "analyze_json", "statistics", "chart", "transform"]},
    {"id": "terminal", "name": "Terminal", "actions": ["run", "processes", "env", "network", "open"]},
    {"id": "database", "name": "Database", "actions": ["tables", "query", "create_table", "import", "export"]},
    {"id": "documents", "name": "Documents", "actions": ["upload", "list", "search", "delete"]},
    {"id": "media", "name": "Media", "actions": ["pdf", "excel", "zip", "html", "markdown", "video_scene"]},
    {"id": "sites", "name": "Sites", "actions": ["list", "preview", "template"]},
    {"id": "weather", "name": "Weather", "actions": ["current", "forecast", "alerts"]},
    {"id": "calculator", "name": "Calculator", "actions": ["calculate", "convert", "scientific"]},
    {"id": "api-tester", "name": "API Tester", "actions": ["GET", "POST", "PUT", "DELETE"]},
    {"id": "system", "name": "System", "actions": ["info", "processes", "disk", "network", "tools"]},
    {"id": "markdown", "name": "Markdown", "actions": ["create", "edit", "export", "template"]},
    {"id": "email-draft", "name": "Email Draft", "actions": ["draft", "reply", "template"]},
    {"id": "scheduler", "name": "Scheduler", "actions": ["add", "list", "complete", "reminder"]},
    {"id": "vscode", "name": "VS Code", "actions": ["open", "extensions", "recent"]},
]

SYSTEM_PROMPT = """You are AuraCode, a terminal coding agent running on the user's desktop.
You can inspect files, write files, and run shell commands through tools.

IMPORTANT: For simple greetings (hi, hello, hey, thanks, bye, etc.) or general questions
that do NOT require file operations, just respond with a message and empty actions array.
Do NOT call list_files for greetings or conversational messages.

For questions about the codebase, respond directly if you know the answer.
Only call list_files when you actually need to know which files exist.
Only call read_file when you need to see file contents to answer a question.
Only call write_file when the user explicitly asks to create or edit a file.
Only call run_command when the user asks to run something.

Always respond with valid JSON:
{
  "message": "your answer for the user",
  "actions": []
}

When actions are needed:
{
  "message": "short explanation of what you will do",
  "actions": [
    {"tool": "list_files", "path": "."},
    {"tool": "read_file", "path": "app.py"},
    {"tool": "write_file", "path": "app.py", "content": "..."},
    {"tool": "run_command", "command": "python -m uvicorn app.main:app --reload --port 8000"},
    {"tool": "export_to_downloads", "source": "static", "name": "my-website"}
  ]
}

Rules:
- Use relative paths only.
- Never access files outside the current workspace.
- Do NOT auto-run list_files on every message. Only when needed.
- If a file is not found, use list_files and choose the closest real file.
- For this assistant app, the main UI files are usually static/index.html,
  static/styles.css, static/app.js, and the backend files are app/main.py,
  app/rag.py, app/llm.py, app/codegen.py, and app/config.py.
- Prefer reading files before editing.
- Ask before destructive commands.
- Keep actions small and practical.
- Treat small spelling mistakes in the user's request as normal language.
- Do not invent files, command output, installed tools, URLs, credentials, or completed work.
- If tool results show an error, explain the exact error and the next real fix.
- Your message must be a useful answer, not filler.
- Do not try to run python app.py unless an app.py file really exists.
- For this FastAPI assistant, run python -m uvicorn app.main:app --reload --port 8000.
- For generated static websites, do not run Python. Save HTML/CSS/JS files inside generated_projects/<project-name>/.
- If the user asks to put files in Downloads, use export_to_downloads after creating the files in the workspace.
"""


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"

def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"

def _cyan(text: str) -> str:
    return f"\033[36m{text}\033[0m"

def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"

def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"

def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m"

def _magenta(text: str) -> str:
    return f"\033[35m{text}\033[0m"

def _blue(text: str) -> str:
    return f"\033[34m{text}\033[0m"

def _white(text: str) -> str:
    return f"\033[97m{text}\033[0m"


def _spinner():
    frames = ["   ", ".  ", ".. ", "..."]
    i = 0
    while getattr(_spinner, "running", False):
        sys.stdout.write(f"\r  {_cyan(frames[i % len(frames)])} ")
        sys.stdout.flush()
        time.sleep(0.4)
        i += 1
    sys.stdout.write("\r" + " " * 20 + "\r")
    sys.stdout.flush()


def _start_spinner():
    _spinner.running = True
    t = threading.Thread(target=_spinner, daemon=True)
    t.start()
    return t

def _stop_spinner():
    _spinner.running = False
    time.sleep(0.15)


IGNORE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}


def safe_path(path: str) -> Path:
    candidate = (WORKSPACE / path).resolve()
    if not str(candidate).startswith(str(WORKSPACE)):
        raise ValueError("Path escapes workspace.")
    return candidate


def list_files(path: str = ".") -> str:
    root = safe_path(path)
    if not root.exists():
        return "Path does not exist."
    lines = []
    def _walk(dir_path: Path, prefix: str = "", depth: int = 0):
        if depth > 4:
            return
        entries = sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        entries = [e for e in entries if e.name not in IGNORE_DIRS and e.suffix != ".pyc"]
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "\\--- " if is_last else "|--- "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                ext = "    " if is_last else "|   "
                _walk(entry, prefix + ext, depth + 1)
            else:
                size = entry.stat().st_size
                if size > 1024 * 1024:
                    size_str = f"{size // (1024*1024)}MB"
                elif size > 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size}B"
                lines.append(f"{prefix}{connector}{entry.name}  ({size_str})")
    _walk(root)
    return "\n".join(lines[:120]) + ("\n... more files" if len(lines) > 120 else "") or "No files found."


def read_file(path: str) -> str:
    target = safe_path(path)
    if not target.exists() or not target.is_file():
        return "File not found."
    return target.read_text(encoding="utf-8", errors="ignore")[:30000]


def write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {target.relative_to(WORKSPACE)}"


def export_to_downloads(source: str = ".", name: str = "auracode-export") -> str:
    source_path = safe_path(source)
    if not source_path.exists():
        return "Export source does not exist."
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in name).strip("-") or "auracode-export"
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    target = downloads / safe_name
    counter = 2
    while target.exists():
        target = downloads / f"{safe_name}-{counter}"
        counter += 1
    if source_path.is_dir():
        ignore = shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "vector_store.sqlite3")
        shutil.copytree(source_path, target, ignore=ignore)
    else:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target / source_path.name)
    return f"Exported to {target}"


def run_command(command: str) -> str:
    blocked = ["rm ", "del ", "format ", "git reset", "rmdir ", "Remove-Item"]
    if any(item.lower() in command.lower() for item in blocked):
        return "Blocked destructive command. Ask the user to run it manually."
    result = subprocess.run(
        command, cwd=WORKSPACE, shell=True, text=True, capture_output=True, timeout=60,
    )
    output = (result.stdout + result.stderr).strip()
    return output[:30000] or f"Command exited with code {result.returncode}."


def command_exists(name: str) -> bool:
    return bool(shutil.which(name))


def run_tool_command(command: list[str], timeout: int = 12) -> str:
    try:
        result = subprocess.run(command, cwd=WORKSPACE, text=True, capture_output=True, timeout=timeout)
        output = (result.stdout + result.stderr).strip()
        return output[:12000] or f"Command exited with code {result.returncode}."
    except FileNotFoundError:
        return f"{command[0]} is not installed or not in PATH."
    except Exception as exc:
        return f"Error: {exc}"


def plugin_status(plugin: str) -> str:
    plugin = plugin.lower().strip()
    if plugin == "git":
        if not command_exists("git"):
            return f"{_red('x')} Git: not installed"
        ver = run_tool_command(["git", "--version"])
        return f"{_green('+')} Git: {ver}"
    if plugin in {"github", "gh"}:
        if not command_exists("gh"):
            return f"{_red('x')} GitHub CLI: not installed"
        return f"{_green('+')} GitHub CLI: {run_tool_command(['gh', 'auth', 'status'])}"
    if plugin in {"vscode", "code"}:
        if not command_exists("code"):
            return f"{_red('x')} VS Code: not installed"
        return f"{_green('+')} VS Code: {run_tool_command(['code', '--version'])}"
    if plugin in {"terminal", "powershell"}:
        return f"{_green('+')} Terminal: ready"
    return f"{_yellow('?')} {plugin}: check via web UI"


def connect_plugin(plugin: str) -> str:
    plugin = plugin.lower().strip()
    if plugin in {"github", "gh"}:
        if not command_exists("gh"):
            return "GitHub CLI not installed."
        subprocess.Popen(
            ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "gh auth login"],
            cwd=WORKSPACE, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return "Opened GitHub login terminal."
    if plugin in {"vscode", "code"}:
        if not command_exists("code"):
            return "VS Code not in PATH."
        subprocess.Popen(["code", "."], cwd=WORKSPACE)
        return "Opened in VS Code."
    return plugin_status(plugin)


def execute_actions(actions: list[dict]) -> str:
    results = []
    for action in actions:
        tool = action.get("tool")
        try:
            if tool == "list_files":
                result = list_files(action.get("path", "."))
            elif tool == "read_file":
                result = read_file(action.get("path", ""))
            elif tool == "write_file":
                result = write_file(action.get("path", ""), action.get("content", ""))
            elif tool == "run_command":
                command = action.get("command", "")
                if command.strip().lower() == "python app.py" and not (WORKSPACE / "app.py").exists():
                    result = "Use: python -m uvicorn app.main:app --reload --port 8000"
                else:
                    result = run_command(command)
            elif tool == "export_to_downloads":
                result = export_to_downloads(action.get("source", "."), action.get("name", "auracode-export"))
            else:
                result = f"Unknown tool: {tool}"
        except Exception as exc:
            result = f"Error: {exc}"
        results.append(f"[{_cyan(tool)}] {result[:2000]}")
    return "\n".join(results)


def handle_builtin(user_input: str) -> bool:
    normalized = user_input.strip().lower()
    targets = {
        "open app": WORKSPACE, "open workspace": WORKSPACE,
        "open project": WORKSPACE / "generated_projects",
        "open projects": WORKSPACE / "generated_projects",
        "open downloads": Path.home() / "Downloads",
    }
    target = targets.get(normalized)
    if not target:
        return False
    target.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["explorer", str(target)])
    print(f"\n  {_green('opened')} {target}\n")
    return True


def handle_slash_command(user_input: str) -> bool:
    if not user_input.startswith("/"):
        return False
    command, _, value = user_input[1:].partition(" ")
    command = command.lower().strip()
    value = value.strip()

    if command in {"help", "?"}:
        print(f"""
  {_bold(_white('Commands'))}

  {_cyan('/agents')}                {_dim('list all available agents')}
  {_cyan('/agent')}  <name>         {_dim('switch to an agent')}
  {_cyan('/plugins')}               {_dim('list all plugins with status')}
  {_cyan('/plugin')}  <name>         {_dim('check plugin status')}
  {_cyan('/connect')} <name>         {_dim('connect a plugin (github, vscode)')}

  {_cyan('/files')}   [path]         {_dim('list workspace files')}
  {_cyan('/read')}    <path>         {_dim('read a file')}
  {_cyan('/run')}     <command>      {_dim('run a shell command')}
  {_cyan('/export')}  [path] [name]  {_dim('export to Downloads')}

  {_cyan('/open')}                   {_dim('open workspace in explorer')}
  {_cyan('/history')}                {_dim('view past chats')}
  {_cyan('/device')}                 {_dim('show device info')}
  {_cyan('/clear')}                  {_dim('clear screen')}
  {_cyan('/quit')}                   {_dim('exit AuraCode')}
""")
        return True

    if command == "clear":
        print("\033[2J\033[H", end="")
        return True

    if command == "agents":
        print(f"\n  {_bold(_white('Agents'))}  ({len(AGENTS)} available)\n")
        for a in AGENTS:
            print(f"    {_cyan(a['id'].ljust(12))} {_dim(a['desc'][:55])}")
        print(f"\n  {_dim('Use /agent <name> to switch')}\n")
        return True

    if command == "agent":
        if not value:
            print(f"  {_dim('Usage: /agent <name>')}")
        else:
            found = [a for a in AGENTS if a["id"] == value.lower()]
            if found:
                a = found[0]
                print(f"\n  {_green('+')} Agent: {_bold(a['name'])}  {_dim(a['desc'])}  model: {a['model']}\n")
            else:
                print(f"  {_red('x')} Agent '{value}' not found. Use /agents to list all.")
        return True

    if command == "plugins":
        print(f"\n  {_bold(_white('Plugins'))}  ({len(PLUGINS)} available)\n")
        for p in PLUGINS:
            status = plugin_status(p["id"].split("-")[0] if "-" in p["id"] else p["id"])
            actions_str = ", ".join(p["actions"][:5])
            if len(p["actions"]) > 5:
                actions_str += f" +{len(p['actions'])-5}"
            print(f"    {_cyan(p['id'].ljust(14))} {status}  {_dim(actions_str)}")
        print()
        return True

    if command == "plugin":
        if not value:
            print(f"  {_dim('Usage: /plugin <name>')}")
        else:
            print(f"\n  {plugin_status(value)}\n")
        return True

    if command == "connect":
        if not value:
            print(f"  {_dim('Usage: /connect github|vscode|terminal')}")
        else:
            print(f"\n  {connect_plugin(value)}\n")
        return True

    if command in {"files", "ls"}:
        print(f"\n  {_bold(_white('Files'))}\n")
        for line in (list_files(value or ".") or "No files found.").split("\n"):
            print(f"    {line}")
        print()
        return True

    if command == "read":
        if not value:
            print(f"  {_dim('Usage: /read <path>')}")
        else:
            content = read_file(value)
            print(f"\n  {_bold(_white(value))}\n")
            for i, line in enumerate(content.split("\n"), 1):
                print(f"    {_dim(str(i).rjust(4))}  {line}")
            print()
        return True

    if command == "run":
        if not value:
            print(f"  {_dim('Usage: /run <command>')}")
        else:
            print(f"\n  {_cyan('$')} {_dim(value)}")
            result = run_command(value)
            for line in result.split("\n")[:40]:
                print(f"    {line}")
            if len(result.split("\n")) > 40:
                print(f"    {_dim('... more output')}")
            print()
        return True

    if command == "open":
        subprocess.Popen(["explorer", str(WORKSPACE)])
        print(f"\n  {_green('opened')} {WORKSPACE}\n")
        return True

    if command in {"projects", "generated"}:
        target = WORKSPACE / "generated_projects"
        target.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(target)])
        print(f"\n  {_green('opened')} {target}\n")
        return True

    if command == "downloads":
        target = Path.home() / "Downloads"
        subprocess.Popen(["explorer", str(target)])
        print(f"\n  {_green('opened')} {target}\n")
        return True

    if command == "export":
        parts = value.split(maxsplit=1)
        source = parts[0] if parts else "."
        name = parts[1] if len(parts) > 1 else "auracode-export"
        result = export_to_downloads(source, name)
        print(f"\n  {_green('exported')} {result}\n")
        return True

    if command == "history":
        chats = get_all_chats()
        if chats:
            print(f"\n  {_bold(_white('Past chats'))} ({len(chats)} total)\n")
            for c in chats[:10]:
                print(f"    {_dim(c['chat_id'][:16])}  {_dim(str(c['message_count']) + ' msgs')}  {c['last_message'][:35]}")
        else:
            print("  No past chats yet.")
        print()
        return True

    if command == "device":
        info = {
            "device": get_device_name(),
            "device_id": get_device_id()[:16],
            "workspace": str(WORKSPACE),
            "facts": len(recall_facts()),
            "patterns": len(get_learned_patterns()),
        }
        print(f"\n  {_bold(_white('Device Info'))}\n")
        for k, v in info.items():
            print(f"    {_cyan(k.ljust(12))} {v}")
        print()
        return True

    print(f"  {_dim('Unknown command. Type /help')}")
    return True


def ask_agent(user_input: str, tool_results: str = "", chat_history: list[dict] = None) -> dict:
    memory_ctx = build_memory_context()
    system = SYSTEM_PROMPT
    if memory_ctx:
        system += f"\n\nUSER MEMORY (this device only):\n{memory_ctx}"

    messages = [{"role": "system", "content": system}]
    if chat_history:
        for msg in chat_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    if tool_results:
        messages.append({
            "role": "user",
            "content": f"Tool results:\n{tool_results}\n\nUser request: {user_input}",
        })
    else:
        messages.append({"role": "user", "content": user_input})

    content = chat_completion(messages, temperature=0.1, json_mode=True)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "message": "Could not parse response. Please try again.",
            "actions": [],
        }


def run_agent_turn(user_input: str, chat_id: str) -> None:
    extract_facts_from_message(user_input)
    store_chat_message(chat_id, "user", user_input)
    history = get_chat_history(chat_id, limit=30)

    tool_results = ""
    for _ in range(5):
        spinner = _start_spinner()
        try:
            response = ask_agent(user_input, tool_results, history)
        finally:
            _stop_spinner()

        message = response.get("message", "")
        actions = response.get("actions", [])

        if message:
            print(f"\n  {message}\n")
            store_chat_message(chat_id, "assistant", message, "auracode")

        if not actions:
            return

        for action in actions:
            tool = action.get("tool", "")
            detail = action.get("path", action.get("command", action.get("source", "")))
            if tool == "write_file":
                detail = action.get("path", "")
            if detail and len(str(detail)) > 60:
                detail = str(detail)[:57] + "..."
            print(f"  {_magenta('>')} {_cyan(tool)} {_dim(str(detail))}")

        spinner = _start_spinner()
        try:
            tool_results = execute_actions(actions)
        finally:
            _stop_spinner()

        if tool_results.strip():
            preview_lines = tool_results.strip().split("\n")[:10]
            preview = "\n".join(preview_lines)
            if len(tool_results.strip().split("\n")) > 10:
                preview += f"\n  {_dim('... ' + str(len(tool_results.strip().split(chr(10))) - 10) + ' more lines')}"
            print(f"  {preview}\n")


def main() -> None:
    chat_id = f"cli_{get_device_id()}_{uuid4().hex[:8]}"

    print()
    print(f"  {_bold(_white('AuraCode'))}  {_dim('v1.0')}")
    print(f"  {_dim('Type your message or /help for commands')}")
    print()

    while True:
        try:
            user_input = input(f"  {_green('>')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "/quit"}:
            print(f"\n  {_dim('bye')}\n")
            break
        try:
            if handle_builtin(user_input):
                continue
            if handle_slash_command(user_input):
                continue
            run_agent_turn(user_input, chat_id)
        except KeyboardInterrupt:
            print(f"\n  {_dim('interrupted')}\n")
            continue
        except Exception as exc:
            print(f"\n  {_red('error:')} {exc}\n")


if __name__ == "__main__":
    main()
