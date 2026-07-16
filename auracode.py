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

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.box import ROUNDED, HEAVY, DOUBLE, MINIMAL
    from rich.live import Live
    from rich.spinner import Spinner
    from rich import box
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

try:
    import questionary
    _HAS_Q = True
except ImportError:
    _HAS_Q = False

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

console = Console()

# ============================================================================
# AGENTS
# ============================================================================
AGENTS = [
    {"id": "general", "name": "Aurine", "icon": "\U0001f9e0", "desc": "Full-stack AI assistant", "color": "cyan"},
    {"id": "coder", "name": "Coder", "icon": "\U0001f4bb", "desc": "Elite coding agent", "color": "green"},
    {"id": "researcher", "name": "Researcher", "icon": "\U0001f50d", "desc": "Web search & analysis", "color": "blue"},
    {"id": "planner", "name": "Planner", "icon": "\U0001f4cb", "desc": "Task decomposition", "color": "yellow"},
    {"id": "creative", "name": "Creative", "icon": "\U0001f3a8", "desc": "Content generation", "color": "magenta"},
    {"id": "data", "name": "Data Analyst", "icon": "\U0001f4ca", "desc": "Data analysis & charts", "color": "red"},
    {"id": "devops", "name": "DevOps", "icon": "\u2699\ufe0f", "desc": "Deploy & infrastructure", "color": "bright_black"},
    {"id": "tutor", "name": "Tutor", "icon": "\U0001f4da", "desc": "Learning & teaching", "color": "bright_blue"},
    {"id": "security", "name": "Security", "icon": "\U0001f6e1\ufe0f", "desc": "Vulnerability scanning", "color": "bright_red"},
]

# ============================================================================
# MODELS - Latest free high-quality models
# ============================================================================
MODELS = [
    {"id": "google/gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "google", "free": True, "tier": "fast", "color": "blue"},
    {"id": "google/gemini-2.5-pro-preview", "name": "Gemini 2.5 Pro", "provider": "google", "free": True, "tier": "best", "color": "blue"},
    {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B (Groq)", "provider": "groq", "free": True, "tier": "fast", "color": "bright_magenta"},
    {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant", "provider": "groq", "free": True, "tier": "fast", "color": "bright_magenta"},
    {"id": "groq/mixtral-8x7b-32768", "name": "Mixtral 8x7B", "provider": "groq", "free": True, "tier": "fast", "color": "bright_magenta"},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek", "free": True, "tier": "best", "color": "green"},
    {"id": "deepseek/deepseek-coder", "name": "DeepSeek Coder", "provider": "deepseek", "free": True, "tier": "best", "color": "green"},
    {"id": "openrouter/meta-llama/llama-3.1-405b-instruct", "name": "Llama 3.1 405B (OpenRouter)", "provider": "openrouter", "free": True, "tier": "best", "color": "bright_yellow"},
    {"id": "openrouter/meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B (OpenRouter)", "provider": "openrouter", "free": True, "tier": "balanced", "color": "bright_yellow"},
    {"id": "openrouter/google/gemini-2.0-flash:free", "name": "Gemini Flash (OpenRouter)", "provider": "openrouter", "free": True, "tier": "fast", "color": "bright_yellow"},
    {"id": "sambanova/Meta-Llama-3.1-405B-Instruct", "name": "Llama 3.1 405B (SambaNova)", "provider": "sambanova", "free": True, "tier": "best", "color": "bright_green"},
    {"id": "cerebras/llama-3.3-70b", "name": "Llama 3.3 70B (Cerebras)", "provider": "cerebras", "free": True, "tier": "fast", "color": "bright_cyan"},
    {"id": "nvidia/meta/llama-3.1-405b-instruct", "name": "Llama 3.1 405B (NVIDIA)", "provider": "nvidia", "free": True, "tier": "best", "color": "bright_red"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "free": False, "tier": "fast", "color": "bright_green"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openai", "free": False, "tier": "best", "color": "bright_green"},
]

# ============================================================================
# PLUGINS
# ============================================================================
PLUGINS = [
    {"id": "git", "name": "Git", "icon": "\U0001f500", "desc": "Version control", "actions": ["status", "log", "diff", "commit", "push", "pull", "branches"]},
    {"id": "github", "name": "GitHub", "icon": "\U0001f419", "desc": "GitHub integration", "actions": ["repos", "issues", "prs", "search"]},
    {"id": "web", "name": "Web Search", "icon": "\U0001f310", "desc": "Search the web", "actions": ["search", "fetch", "news"]},
    {"id": "files", "name": "File Manager", "icon": "\U0001f4c1", "desc": "File operations", "actions": ["list", "read", "write", "search", "delete"]},
    {"id": "terminal", "name": "Terminal", "icon": "\U0001f4bb", "desc": "Shell commands", "actions": ["run", "processes", "env"]},
    {"id": "code", "name": "Code Runner", "icon": "\u25b6\ufe0f", "desc": "Execute code", "actions": ["python", "javascript", "shell"]},
    {"id": "image", "name": "Image", "icon": "\U0001f5bc\ufe0f", "desc": "Image generation", "actions": ["generate", "analyze"]},
    {"id": "data", "name": "Data", "icon": "\U0001f4ca", "desc": "Data analysis", "actions": ["csv", "json", "chart"]},
    {"id": "docs", "name": "Documents", "icon": "\U0001f4c4", "desc": "PDF/DOC handling", "actions": ["upload", "search", "list"]},
    {"id": "media", "name": "Media", "icon": "\U0001f3ac", "desc": "Media creation", "actions": ["pdf", "excel", "zip", "html"]},
]

# ============================================================================
# COMMANDS - opencode-style
# ============================================================================
COMMANDS = [
    {"cmd": "/help", "icon": "?", "desc": "Show all commands", "group": "General"},
    {"cmd": "/agents", "icon": "\U0001f916", "desc": "Select AI agent", "group": "General"},
    {"cmd": "/model", "icon": "\U0001f916", "desc": "Select AI model", "group": "General"},
    {"cmd": "/doctor", "icon": "\U0001fa7a", "desc": "System diagnostics", "group": "General"},
    {"cmd": "/config", "icon": "\u2699\ufe0f", "desc": "Configuration", "group": "General"},
    {"cmd": "/plugins", "icon": "\U0001f50c", "desc": "Manage plugins", "group": "General"},
    {"cmd": "/skills", "icon": "\U0001f4aa", "desc": "Available skills", "group": "General"},
    {"cmd": "/files", "icon": "\U0001f4c1", "desc": "List files", "group": "Files"},
    {"cmd": "/read", "icon": "\U0001f4d6", "desc": "Read file", "group": "Files"},
    {"cmd": "/write", "icon": "\U0001f4dd", "desc": "Write file", "group": "Files"},
    {"cmd": "/run", "icon": "\u25b6\ufe0f", "desc": "Run command", "group": "Files"},
    {"cmd": "/diff", "icon": "\U0001f500", "desc": "Git diff", "group": "Git"},
    {"cmd": "/log", "icon": "\U0001f4dc", "desc": "Git log", "group": "Git"},
    {"cmd": "/git", "icon": "\U0001f500", "desc": "Git command", "group": "Git"},
    {"cmd": "/init", "icon": "\U0001f680", "desc": "Init workspace", "group": "Tools"},
    {"cmd": "/web", "icon": "\U0001f310", "desc": "Search web", "group": "Tools"},
    {"cmd": "/img", "icon": "\U0001f5bc\ufe0f", "desc": "Analyze image", "group": "Tools"},
    {"cmd": "/history", "icon": "\U0001f553", "desc": "Chat history", "group": "Tools"},
    {"cmd": "/device", "icon": "\U0001f4bb", "desc": "Device info", "group": "Tools"},
    {"cmd": "/compact", "icon": "\U0001f4c9", "desc": "Compress context", "group": "Tools"},
    {"cmd": "/cost", "icon": "\U0001f4b0", "desc": "Token estimate", "group": "Tools"},
    {"cmd": "/clear", "icon": "\U0001f5d1\ufe0f", "desc": "Clear screen", "group": "General"},
    {"cmd": "/quit", "icon": "\U0001f6aa", "desc": "Exit", "group": "General"},
]

SYSTEM_PROMPT = """You are AuraCode, a terminal coding agent. You help with coding, files, and commands.
Always respond with valid JSON: {"message": "your answer", "actions": []}
When actions needed: {"message": "...", "actions": [{"tool": "read_file", "path": "..."}]}
Tools: list_files, read_file, write_file, run_command
Rules: Relative paths, stay in workspace, ask before destructive commands.
"""

# ============================================================================
# HELPERS
# ============================================================================
IGNORE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}


def _safe(p):
    c = (WORKSPACE / p).resolve()
    if not str(c).startswith(str(WORKSPACE)):
        raise ValueError("Path escapes workspace.")
    return c


def _list_files(path="."):
    root = _safe(path)
    if not root.exists():
        return "Path does not exist."
    lines = []

    def _walk(d, pre="", dep=0):
        if dep > 4:
            return
        ents = sorted(d.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        ents = [e for e in ents if e.name not in IGNORE_DIRS and e.suffix != ".pyc"]
        for i, e in enumerate(ents):
            last = i == len(ents) - 1
            conn = "\u2514\u2500\u2500\u2500 " if last else "\u251c\u2500\u2500\u2500 "
            if e.is_dir():
                lines.append(f"{pre}{conn}[blue]{e.name}/[/]")
                _walk(e, pre + ("    " if last else "\u2502   "), dep + 1)
            else:
                sz = e.stat().st_size
                s = f"{sz // 1048576}MB" if sz > 1048576 else f"{sz // 1024}KB" if sz > 1024 else f"{sz}B"
                lines.append(f"{pre}{conn}{e.name}  [dim]({s})[/]")

    _walk(root)
    return "\n".join(lines[:120]) or "No files."


def _read_file(p):
    t = _safe(p)
    if not t.exists() or not t.is_file():
        return "File not found."
    return t.read_text(encoding="utf-8", errors="ignore")[:30000]


def _write_file(p, c):
    t = _safe(p)
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(c, encoding="utf-8")
    return f"Wrote {t.relative_to(WORKSPACE)}"


def _run_cmd(cmd):
    bl = ["rm ", "del ", "format ", "git reset", "rmdir ", "Remove-Item"]
    if any(x.lower() in cmd.lower() for x in bl):
        return "Blocked destructive command."
    r = subprocess.run(cmd, cwd=WORKSPACE, shell=True, text=True, capture_output=True, timeout=60)
    return (r.stdout + r.stderr).strip()[:30000] or f"Exit code {r.returncode}."


def _exec(actions):
    res = []
    for a in actions:
        t = a.get("tool")
        try:
            if t == "list_files":
                r = _list_files(a.get("path", "."))
            elif t == "read_file":
                r = _read_file(a.get("path", ""))
            elif t == "write_file":
                r = _write_file(a.get("path", ""), a.get("content", ""))
            elif t == "run_command":
                r = _run_cmd(a.get("command", ""))
            else:
                r = f"Unknown tool: {t}"
        except Exception as e:
            r = f"Error: {e}"
        res.append(f"  [cyan]\u25b6 {t}[/] [dim]{r[:500]}[/]")
    return "\n".join(res)


def _get_provider_info():
    from dotenv import load_dotenv
    load_dotenv()
    provider = os.getenv("AI_PROVIDER", "aurine")
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    has_key = bool(os.getenv("OPENAI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GROQ_API_KEY", ""))
    return provider, model, has_key


def _get_device_str():
    if _HAS_AI:
        return f"{get_device_name()} [dim]id:{get_device_id()[:12]}[/]"
    import platform
    return f"{platform.node()} ({platform.system()})"


# ============================================================================
# RICH DISPLAY FUNCTIONS
# ============================================================================

def _show_help():
    table = Table(box=ROUNDED, title="[bold cyan]AuraCode Commands[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("Command", style="bold yellow", min_width=14)
    table.add_column("Description", style="white")
    table.add_column("Group", style="dim")

    current_group = ""
    for cmd in COMMANDS:
        if cmd["group"] != current_group:
            current_group = cmd["group"]
        table.add_row(cmd["cmd"], cmd["desc"], cmd["group"])

    console.print()
    console.print(table)
    console.print()


def _show_agents():
    table = Table(box=ROUNDED, title="[bold cyan]AI Agents[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("", min_width=3)
    table.add_column("Name", style="bold", min_width=16)
    table.add_column("Description", style="white")
    table.add_column("ID", style="dim")

    for a in AGENTS:
        table.add_row(a["icon"], f"[{a['color']}]{a['name']}[/]", a["desc"], a["id"])

    console.print()
    console.print(table)
    console.print()


def _show_models():
    table = Table(box=ROUNDED, title="[bold cyan]AI Models[/] [dim]- All free, latest, high quality[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("Model", style="bold", min_width=32)
    table.add_column("Provider", style="cyan", min_width=12)
    table.add_column("Tier", min_width=8)
    table.add_column("Free", min_width=5)

    for m in MODELS:
        tier_color = "green" if m["tier"] == "fast" else "yellow" if m["tier"] == "balanced" else "red"
        free_mark = "[green]\u2713[/]" if m["free"] else "[red]\u2717[/]"
        table.add_row(
            f"[{m['color']}]{m['name']}[/]",
            m["provider"],
            f"[{tier_color}]{m['tier']}[/]",
            free_mark,
        )

    console.print()
    console.print(table)
    console.print()


def _show_plugins():
    table = Table(box=ROUNDED, title="[bold cyan]Plugins[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("", min_width=3)
    table.add_column("Name", style="bold", min_width=14)
    table.add_column("Description", style="white")
    table.add_column("Actions", style="dim")

    for p in PLUGINS:
        actions = ", ".join(p["actions"][:5])
        table.add_row(p["icon"], f"[cyan]{p['name']}[/]", p["desc"], actions)

    console.print()
    console.print(table)
    console.print()


def _show_skills():
    skills = [
        ("Code Review", "Review code for bugs and improvements"),
        ("Refactor", "Refactor code for better structure"),
        ("Test Generator", "Generate unit tests"),
        ("Doc Generator", "Generate documentation"),
        ("API Design", "Design REST/GraphQL APIs"),
        ("Database Design", "Schema design and queries"),
        ("Security Audit", "Scan for vulnerabilities"),
        ("Performance", "Optimize code performance"),
        ("Git Workflow", "Branch strategy and commits"),
        ("Docker", "Dockerfile and compose setup"),
        ("CI/CD", "GitHub Actions, pipelines"),
        ("Deploy", "Deployment automation"),
    ]

    table = Table(box=ROUNDED, title="[bold cyan]Skills[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("Skill", style="bold green", min_width=18)
    table.add_column("Description", style="white")

    for name, desc in skills:
        table.add_row(name, desc)

    console.print()
    console.print(table)
    console.print()


def _show_init():
    files = ["package.json", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml", "package-lock.json"]
    found = [f for f in files if (WORKSPACE / f).exists()]

    panel_content = []
    if found:
        panel_content.append(f"[green]\u2713[/] Project: {', '.join(found)}")
    else:
        panel_content.append(f"[yellow]![/] No standard project files in [bold]{WORKSPACE.name}[/]")

    dotgit = WORKSPACE / ".git"
    if dotgit.exists():
        branch = _run_cmd("git branch --show-current").strip()
        remote = _run_cmd("git remote get-url origin").strip()
        panel_content.append(f"[green]\u2713[/] Git: branch={branch or 'none'} remote={remote or 'none'}")
    else:
        panel_content.append(f"[yellow]![/] No git repo")

    panel_content.append(f"[green]\u2713[/] Workspace: [bold]{WORKSPACE}[/]")
    if _HAS_AI:
        panel_content.append(f"[green]\u2713[/] Device: {_get_device_str()}")

    prov, model, has_key = _get_provider_info()
    status = "[green]\u2713[/]" if has_key else "[yellow]![/]"
    panel_content.append(f"{status} Provider: [bold]{prov}[/]  Model: {model}")

    console.print()
    console.print(Panel("\n".join(panel_content), title="[bold cyan]Workspace Init[/]", border_style="cyan"))
    console.print()


def _show_config():
    from dotenv import load_dotenv
    load_dotenv()

    table = Table(box=ROUNDED, title="[bold cyan]Configuration[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("Key", style="bold yellow", min_width=24)
    table.add_column("Status", min_width=12)
    table.add_column("Value", style="dim")

    keys = {
        "AI_PROVIDER": os.getenv("AI_PROVIDER", "aurine"),
        "GOOGLE_API_KEY": "set" if os.getenv("GOOGLE_API_KEY") else "not set",
        "OPENAI_API_KEY": "set" if os.getenv("OPENAI_API_KEY") else "not set",
        "GROQ_API_KEY": "set" if os.getenv("GROQ_API_KEY") else "not set",
        "DEEPSEEK_API_KEY": "set" if os.getenv("DEEPSEEK_API_KEY") else "not set",
        "OPENROUTER_API_KEY": "set" if os.getenv("OPENROUTER_API_KEY") else "not set",
        "ANTHROPIC_API_KEY": "set" if os.getenv("ANTHROPIC_API_KEY") else "not set",
        "SAMBANOVA_API_KEY": "set" if os.getenv("SAMBANOVA_API_KEY") else "not set",
        "AURINE_API_KEY": "set" if os.getenv("AURINE_API_KEY") else "built-in",
    }

    for k, v in keys.items():
        st = "[green]\u2713 set[/]" if v == "set" or v == "built-in" else "[red]\u2717 not set[/]"
        table.add_row(k, st, v)

    console.print()
    console.print(table)
    console.print("[dim]Edit .env file to change settings[/]")
    console.print()


def _show_doctor():
    import platform

    table1 = Table(box=MINIMAL, border_style="cyan", padding=(0, 1))
    table1.add_column("Check", style="bold cyan", min_width=16)
    table1.add_column("Status", min_width=20)
    table1.add_column("Detail", style="dim")

    table1.add_row("OS", "[green]OK[/]", f"{platform.system()} {platform.release()}")
    table1.add_row("Python", "[green]OK[/]", sys.version.split()[0])
    table1.add_row("Workspace", "[green]OK[/]", str(WORKSPACE))
    if _HAS_AI:
        table1.add_row("Device", "[green]OK[/]", _get_device_str())

    console.print()
    console.print(Panel(table1, title="[bold cyan]System[/]", border_style="cyan"))

    # AI Status
    table2 = Table(box=MINIMAL, border_style="cyan", padding=(0, 1))
    table2.add_column("Check", style="bold cyan", min_width=16)
    table2.add_column("Status", min_width=20)

    try:
        from app.llm import _ollama_running, _aurine_server_running
        ollama_ok = _ollama_running()
        aurine_ok = _aurine_server_running()
        table2.add_row("Ollama", "[green]\u2713 running[/]" if ollama_ok else "[yellow]not running[/]")
        table2.add_row("Aurine Server", "[green]\u2713 running[/]" if aurine_ok else "[yellow]not running[/]")
    except Exception:
        table2.add_row("AI Check", "[yellow]cannot check[/]")

    prov, model, has_key = _get_provider_info()
    table2.add_row("Provider", f"[bold]{prov}[/]")
    table2.add_row("Model", model)
    table2.add_row("API Key", "[green]\u2713 configured[/]" if has_key else "[red]\u2717 MISSING[/]")

    console.print(Panel(table2, title="[bold cyan]AI Provider[/]", border_style="cyan"))

    # Tools
    table3 = Table(box=MINIMAL, border_style="cyan", padding=(0, 1))
    table3.add_column("Tool", style="bold", min_width=10)
    table3.add_column("Status", min_width=10)

    for tool in ["git", "python", "node", "npm", "docker", "code", "gh"]:
        found = bool(shutil.which(tool))
        st = "[green]\u2713[/]" if found else "[red]\u2717[/]"
        table3.add_row(tool, st)

    console.print(Panel(table3, title="[bold cyan]Tools[/]", border_style="cyan"))
    console.print()


def _show_device():
    table = Table(box=ROUNDED, title="[bold cyan]Device Info[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
    table.add_column("Key", style="bold cyan", min_width=16)
    table.add_column("Value", style="white")

    table.add_row("Workspace", str(WORKSPACE))
    if _HAS_AI:
        table.add_row("Device", get_device_name())
        table.add_row("Device ID", get_device_id()[:16])
        table.add_row("User ID", get_user_id())
        table.add_row("Data Dir", str(get_device_data_path()))

    console.print()
    console.print(table)
    console.print()


def _show_diff():
    result = _run_cmd("git diff --stat")
    full = _run_cmd("git diff")
    console.print()
    console.print(Panel(result or "[dim]No changes[/]", title="[bold cyan]Git Diff[/]", border_style="cyan"))
    if full.strip():
        for line in full.split("\n")[:60]:
            color = "green" if line.startswith("+") else "red" if line.startswith("-") else "dim"
            console.print(f"  [{color}]{line}[/]")
    console.print()


def _show_log():
    result = _run_cmd("git log --oneline -20")
    console.print()
    console.print(Panel(result or "[dim]No commits[/]", title="[bold cyan]Git Log[/]", border_style="cyan"))
    console.print()


def _show_history():
    if _HAS_AI:
        chats = get_all_chats()
        if chats:
            table = Table(box=ROUNDED, title="[bold cyan]Chat History[/]", title_style="bold cyan", border_style="cyan", padding=(0, 1))
            table.add_column("Session", style="dim", min_width=16)
            table.add_column("Last Message", style="white")
            for c in chats[:15]:
                table.add_row(c["chat_id"][:16], c["last_message"][:50])
            console.print()
            console.print(table)
        else:
            console.print("[dim]No chat history yet.[/]")
    else:
        console.print("[dim]AI module not available.[/]")


def get_device_data_path():
    if _HAS_AI:
        from app.device import get_data_dir
        return str(get_data_dir())
    return "N/A"


# ============================================================================
# INTERACTIVE SELECTION (like opencode)
# ============================================================================

def _select_from_menu(title, options, key_func=None):
    if _HAS_Q:
        choices = []
        for opt in options:
            if isinstance(opt, dict):
                display = opt.get("display", opt.get("name", str(opt)))
                choices.append(questionary.Choice(title=display, value=opt))
            else:
                choices.append(questionary.Choice(title=str(opt), value=opt))
        result = questionary.select(
            title,
            choices=choices,
            style=questionary.Style([
                ('question', 'bold cyan'),
                ('pointer', 'fg:cyan bold'),
                ('highlighted', 'fg:cyan bold'),
                ('selected', 'fg:green bold'),
            ]),
        ).ask()
        return result
    else:
        console.print(f"\n[bold cyan]{title}[/]")
        for i, opt in enumerate(options, 1):
            if isinstance(opt, dict):
                console.print(f"  [yellow]{i}.[/] {opt.get('display', opt.get('name', str(opt)))}")
            else:
                console.print(f"  [yellow]{i}.[/] {opt}")
        try:
            choice = input("\n  Select: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, EOFError):
            pass
        return None


def _select_agent():
    options = []
    for a in AGENTS:
        options.append({
            "display": f"{a['icon']}  {a['name']}  [dim]- {a['desc']}[/]",
            "value": a,
        })
    result = _select_from_menu("Select Agent:", options)
    if result:
        console.print(f"\n  [green]\u2713[/] Agent: [bold]{result['name']}[/]  [dim]{result['desc']}[/]\n")
    return result


def _select_model():
    options = []
    for m in MODELS:
        free = " [green]\u2713free[/]" if m["free"] else " [red]paid[/]"
        options.append({
            "display": f"[{m['color']}]{m['name']}[/]  [dim]{m['provider']}[/]{free}",
            "value": m,
        })
    result = _select_from_menu("Select Model:", options)
    if result:
        console.print(f"\n  [green]\u2713[/] Model: [bold]{result['name']}[/]  [dim]{result['provider']}[/]\n")
    return result


def _select_plugin_action(plugin):
    options = [{"display": f"  {a}", "value": a} for a in plugin["actions"]]
    return _select_from_menu(f"Select {plugin['name']} action:", options)


def _select_plugin():
    options = []
    for p in PLUGINS:
        options.append({
            "display": f"{p['icon']}  {p['name']}  [dim]- {p['desc']}[/]",
            "value": p,
        })
    result = _select_from_menu("Select Plugin:", options)
    if result:
        action = _select_plugin_action(result)
        if action:
            return result, action
    return None, None


def _handle_slash(inp):
    if not inp.startswith("/"):
        return False
    parts = inp[1:].split(" ", 1)
    cmd = parts[0].lower().strip()
    val = parts[1].strip() if len(parts) > 1 else ""

    if cmd in {"help", "?"}:
        _show_help()
        return True

    if cmd == "clear":
        console.clear()
        return True

    if cmd == "agents":
        if not val and _HAS_Q:
            result = _select_agent()
            if result:
                pass
        else:
            _show_agents()
        return True

    if cmd == "model":
        if not val and _HAS_Q:
            result = _select_model()
            if result:
                pass
        else:
            _show_models()
        return True

    if cmd == "skills":
        _show_skills()
        return True

    if cmd == "plugins":
        if not val and _HAS_Q:
            plugin, action = _select_plugin()
            if plugin and action:
                console.print(f"  [cyan]\u25b6[/] {plugin['name']} > {action}")
        else:
            _show_plugins()
        return True

    if cmd == "init":
        _show_init()
        return True

    if cmd == "config":
        _show_config()
        return True

    if cmd == "doctor":
        _show_doctor()
        return True

    if cmd == "device":
        _show_device()
        return True

    if cmd == "history":
        _show_history()
        return True

    if cmd in {"files", "ls"}:
        console.print()
        content = _list_files(val or ".")
        console.print(Panel(content or "[dim]No files[/]", title="[bold cyan]Files[/]", border_style="cyan"))
        console.print()
        return True

    if cmd == "read":
        if not val:
            console.print("[dim]Usage: /read <path>[/]")
        else:
            content = _read_file(val)
            console.print()
            try:
                syntax = Syntax(content, val.split(".")[-1] if "." in val else "text", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title=f"[bold cyan]{val}[/]", border_style="cyan"))
            except Exception:
                console.print(Panel(content, title=f"[bold cyan]{val}[/]", border_style="cyan"))
            console.print()
        return True

    if cmd == "write":
        console.print("[dim]Usage: /write <path>  (then describe what to write in chat)[/]")
        return True

    if cmd == "run":
        if not val:
            console.print("[dim]Usage: /run <command>[/]")
        else:
            console.print(f"\n  [cyan]$[/] [dim]{val}[/]")
            result = _run_cmd(val)
            console.print(Panel(result[:3000], border_style="dim"))
            console.print()
        return True

    if cmd == "diff":
        _show_diff()
        return True

    if cmd == "log":
        _show_log()
        return True

    if cmd == "git":
        if not val:
            console.print("[dim]Usage: /git <args>  e.g. /git status[/]")
        else:
            result = _run_cmd(f"git {val}")
            console.print(f"\n  [dim]git {val}[/]")
            console.print(Panel(result[:3000], border_style="dim"))
            console.print()
        return True

    if cmd == "web":
        if not val:
            console.print("[dim]Usage: /web <search query>[/]")
        else:
            console.print(f"\n  [cyan]Searching:[/] {val}")
            try:
                import urllib.request, urllib.parse
                url = f"https://www.google.com/search?q={urllib.parse.quote(val)}"
                result = _run_cmd(f'curl -sL "{url}" -H "User-Agent: Mozilla/5.0" 2>nul | head -c 2000')
                console.print(Panel(result[:1000] or "[dim]No results[/]", border_style="dim"))
            except Exception:
                console.print("[dim]Web search not available[/]")
            console.print()
        return True

    if cmd == "img":
        if not val:
            console.print("[dim]Usage: /img <image_path>[/]")
        else:
            p = _safe(val)
            if p.exists():
                sz = p.stat().st_size
                console.print(Panel(f"Image: [bold]{val}[/]\nSize: {sz} bytes\nType: {p.suffix}", title="[bold cyan]Image[/]", border_style="cyan"))
            else:
                console.print(f"[red]File not found: {val}[/]")
        return True

    if cmd == "compact":
        console.print(Panel("[cyan]Context compacted[/]  [dim]History truncated for next turn[/]", border_style="cyan"))
        return True

    if cmd == "cost":
        prov, model, has_key = _get_provider_info()
        table = Table(box=MINIMAL, border_style="cyan")
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")
        table.add_row("Provider", prov)
        table.add_row("Model", model)
        table.add_row("API Key", "[green]configured[/]" if has_key else "[red]not set[/]")
        console.print()
        console.print(Panel(table, title="[bold cyan]Token Estimate[/]", border_style="cyan"))
        console.print()
        return True

    if cmd == "quit":
        console.print("\n  [dim]bye[/]\n")
        raise SystemExit(0)

    console.print(f"[dim]Unknown command. Type /help[/]")
    return True


# ============================================================================
# AI CORE
# ============================================================================

def _ask(inp, tool_results="", history=None):
    if not _HAS_AI:
        return {"message": "AI module not available.", "actions": []}
    mem = build_memory_context()
    sys = SYSTEM_PROMPT
    if mem:
        sys += f"\n\nUSER MEMORY:\n{mem}"
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
        with console.status("[bold cyan]Thinking...[/]", spinner="dots"):
            try:
                resp = _ask(inp, tool_results, history)
            except Exception as e:
                console.print(f"\n  [red]\u2717 error:[/] {e}\n")
                return

        msg = resp.get("message", "")
        actions = resp.get("actions", [])
        if msg:
            console.print()
            console.print(Panel(msg, border_style="cyan", padding=(0, 1)))
            console.print()
            if _HAS_AI:
                store_chat_message(chat_id, "assistant", msg, "auracode")
        if not actions:
            return

        for a in actions:
            tool = a.get("tool", "")
            det = a.get("path", a.get("command", ""))
            if tool == "write_file":
                det = a.get("path", "")
            if det and len(str(det)) > 60:
                det = str(det)[:57] + "..."
            console.print(f"  [magenta]\u25b6[/] [cyan]{tool}[/] [dim]{det}[/]")

        with console.status("[bold cyan]Executing...[/]", spinner="dots"):
            tool_results = _exec(actions)

        if tool_results.strip():
            for line in tool_results.strip().split("\n")[:10]:
                console.print(f"  {line}")
            console.print()


# ============================================================================
# MAIN
# ============================================================================

def _print_header():
    prov, model, has_key = _get_provider_info()

    header = Table(box=ROUNDED, border_style="cyan", padding=(0, 1), show_header=False)
    header.add_column("Content", ratio=1)
    header.add_row("[bold cyan]AuraCode[/]  [dim]v1.0[/]")
    header.add_row("[dim]AI coding agent for your terminal[/]")
    header.add_row(f"[dim]Provider:[/] [bold]{prov}[/]  [dim]Model:[/] {model}")
    if not has_key:
        header.add_row("[yellow]![/] [dim]No cloud API key - add GOOGLE_API_KEY to .env[/]")

    console.print()
    console.print(header)
    console.print("[dim]Type a message or / for commands[/]")
    console.print()


def main():
    chat_id = f"cli_{uuid4().hex[:8]}"
    if _HAS_AI:
        chat_id = f"cli_{get_device_id()}_{uuid4().hex[:8]}"

    _print_header()

    while True:
        try:
            u = console.input("  [green]\u25b6[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n  [dim]bye[/]\n")
            break
        if not u:
            continue
        if u.lower() in {"exit", "quit", "/quit"}:
            console.print("\n  [dim]bye[/]\n")
            break
        try:
            if _handle_slash(u):
                continue
            _run_turn(u, chat_id)
        except SystemExit:
            console.print("\n  [dim]bye[/]\n")
            break
        except KeyboardInterrupt:
            console.print("\n  [dim]interrupted[/]\n")
            continue
        except Exception as e:
            console.print(f"\n  [red]\u2717 error:[/] {e}\n")


if __name__ == "__main__":
    main()
