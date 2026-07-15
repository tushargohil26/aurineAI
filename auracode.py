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
    {"id": "aurine", "name": "Aurine", "desc": "Full-stack AI assistant", "model": "gpt-4o"},
    {"id": "codex", "name": "Codex", "desc": "Code-focused agent", "model": "gpt-4o"},
    {"id": "researcher", "name": "Researcher", "desc": "Web search and summarization", "model": "gpt-4o-mini"},
    {"id": "analyst", "name": "Analyst", "desc": "Data analysis and charts", "model": "gpt-4o"},
    {"id": "devops", "name": "DevOps", "desc": "Git, CI/CD, deployment", "model": "gpt-4o"},
    {"id": "designer", "name": "Designer", "desc": "HTML/CSS, SVG, UI", "model": "gpt-4o"},
    {"id": "debugger", "name": "Debugger", "desc": "Bug fixing and error analysis", "model": "gpt-4o"},
    {"id": "security", "name": "Security", "desc": "Vulnerability scanning", "model": "gpt-4o"},
]

SYSTEM_PROMPT = """You are AuraCode, a terminal coding agent running on the user's desktop.
You can inspect files, write files, and run shell commands through tools.

IMPORTANT: For simple greetings or general questions that do NOT require file operations,
just respond with a message and empty actions array.

Always respond with valid JSON:
{
  "message": "your answer for the user",
  "actions": []
}

When actions are needed:
{
  "message": "short explanation",
  "actions": [
    {"tool": "list_files", "path": "."},
    {"tool": "read_file", "path": "file.py"},
    {"tool": "write_file", "path": "file.py", "content": "..."},
    {"tool": "run_command", "command": "python -m uvicorn app.main:app --reload --port 8000"},
    {"tool": "export_to_downloads", "source": "static", "name": "my-website"}
  ]
}

Rules:
- Use relative paths only.
- Never access files outside the current workspace.
- Only call tools when actually needed.
- Ask before destructive commands.
- Keep actions small and practical.
"""


class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BG_DARK = "\033[48;5;236m"
    BG_GREEN = "\033[48;5;28m"
    FG_232 = "\033[38;5;232m"

C = _Colors

IGNORE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache"}


def _term_width():
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def _box_line(text, width=None):
    w = width or _term_width()
    inner = w - 4
    if len(text) > inner:
        text = text[:inner - 3] + "..."
    return f"  {C.GRAY}\u2502{C.RESET} {text}{' ' * max(0, inner - len(text))} {C.GRAY}\u2502{C.RESET}"


def _separator(char="\u2500", width=None):
    w = width or _term_width()
    return f"  {C.GRAY}{''.join([char] * (w - 4))}{C.RESET}"


def _top_border(width=None):
    w = width or _term_width()
    return f"  {C.GRAY}\u250C{''.join(['\u2500'] * (w - 4))}\u2510{C.RESET}"


def _bottom_border(width=None):
    w = width or _term_width()
    return f"  {C.GRAY}\u2514{''.join(['\u2500'] * (w - 4))}\u2518{C.RESET}"


def _side_by_side(left, right, width=None):
    w = width or _term_width()
    inner = w - 6
    left_len = len(left)
    right_len = len(right)
    gap = inner - left_len - right_len
    if gap < 1:
        return f"  {C.GRAY}\u2502{C.RESET} {left} {C.GRAY}\u2502{C.RESET}"
    return f"  {C.GRAY}\u2502{C.RESET} {left}{' ' * gap}{right} {C.GRAY}\u2502{C.RESET}"


def _spinner():
    frames = ["\u25F7", "\u25F4", "\u25F5", "\u25F6"]
    i = 0
    while getattr(_spinner, "running", False):
        sys.stdout.write(f"\r  {C.CYAN}{frames[i % len(frames)]}{C.RESET} {C.DIM}thinking...{C.RESET}   ")
        sys.stdout.flush()
        time.sleep(0.3)
        i += 1
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()


def _start_spinner():
    _spinner.running = True
    t = threading.Thread(target=_spinner, daemon=True)
    t.start()
    return t


def _stop_spinner():
    _spinner.running = False
    time.sleep(0.1)


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
            connector = "\u2514\u2500\u2500\u2500 " if is_last else "\u251C\u2500\u2500\u2500 "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                ext = "    " if is_last else "\u2502   "
                _walk(entry, prefix + ext, depth + 1)
            else:
                size = entry.stat().st_size
                if size > 1024 * 1024:
                    size_str = f"{size // (1024*1024)}MB"
                elif size > 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size}B"
                lines.append(f"{prefix}{connector}{entry.name}  {C.DIM}({size_str}){C.RESET}")
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
                result = run_command(action.get("command", ""))
            elif tool == "export_to_downloads":
                result = export_to_downloads(action.get("source", "."), action.get("name", "auracode-export"))
            else:
                result = f"Unknown tool: {tool}"
        except Exception as exc:
            result = f"Error: {exc}"
        results.append(f"  {C.CYAN}\u25B6 {tool}{C.RESET} {result[:500]}")
    return "\n".join(results)


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
        return {"message": "Could not parse response. Please try again.", "actions": []}


def handle_slash_command(user_input: str) -> bool:
    if not user_input.startswith("/"):
        return False
    command, _, value = user_input[1:].partition(" ")
    command = command.lower().strip()
    value = value.strip()

    if command in {"help", "?"}:
        print()
        print(_top_border())
        print(_box_line(f"{C.BOLD}{C.WHITE}AuraCode{C.RESET}  {C.DIM}Commands{C.RESET}"))
        print(_separator())
        print(_box_line(f"  {C.CYAN}/agents{C.RESET}              {C.DIM}list available agents{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/agent{C.RESET}  <name>       {C.DIM}switch agent{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/files{C.RESET}  [path]       {C.DIM}list workspace files{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/read{C.RESET}   <path>       {C.DIM}read a file{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/run{C.RESET}    <command>    {C.DIM}run shell command{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/export{C.RESET} [path] [name]{C.DIM}export to Downloads{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/open{C.RESET}                {C.DIM}open workspace{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/clear{C.RESET}               {C.DIM}clear screen{C.RESET}"))
        print(_box_line(f"  {C.CYAN}/quit{C.RESET}                {C.DIM}exit{C.RESET}"))
        print(_bottom_border())
        print()
        return True

    if command == "clear":
        print("\033[2J\033[H", end="")
        return True

    if command == "agents":
        print()
        print(_top_border())
        print(_box_line(f"{C.BOLD}{C.WHITE}Agents{C.RESET}  {C.DIM}({len(AGENTS)} available){C.RESET}"))
        print(_separator())
        for a in AGENTS:
            print(_box_line(f"  {C.CYAN}{a['id'].ljust(12)}{C.RESET} {C.DIM}{a['desc']}{C.RESET}"))
        print(_bottom_border())
        print()
        return True

    if command == "agent":
        if not value:
            print(f"  {C.DIM}Usage: /agent <name>{C.RESET}")
        else:
            found = [a for a in AGENTS if a["id"] == value.lower()]
            if found:
                a = found[0]
                print(f"\n  {C.GREEN}\u2713{C.RESET} Agent: {C.BOLD}{a['name']}{C.RESET}  {C.DIM}{a['desc']}{C.RESET}  {C.DIM}model: {a['model']}{C.RESET}\n")
            else:
                print(f"  {C.RED}\u2717{C.RESET} Agent '{value}' not found.")
        return True

    if command in {"files", "ls"}:
        print()
        print(_top_border())
        print(_box_line(f"{C.BOLD}{C.WHITE}Files{C.RESET}"))
        print(_separator())
        for line in (list_files(value or ".") or "No files found.").split("\n"):
            print(_box_line(f"  {line}"))
        print(_bottom_border())
        print()
        return True

    if command == "read":
        if not value:
            print(f"  {C.DIM}Usage: /read <path>{C.RESET}")
        else:
            content = read_file(value)
            print()
            print(_top_border())
            print(_box_line(f"{C.BOLD}{C.WHITE}{value}{C.RESET}"))
            print(_separator())
            for i, line in enumerate(content.split("\n"), 1):
                print(_box_line(f"  {C.DIM}{str(i).rjust(4)}{C.RESET}  {line}"))
            print(_bottom_border())
            print()
        return True

    if command == "run":
        if not value:
            print(f"  {C.DIM}Usage: /run <command>{C.RESET}")
        else:
            print(f"\n  {C.CYAN}$ {C.RESET}{C.DIM}{value}{C.RESET}")
            result = run_command(value)
            for line in result.split("\n")[:40]:
                print(f"    {line}")
            if len(result.split("\n")) > 40:
                print(f"    {C.DIM}... more output{C.RESET}")
            print()
        return True

    if command == "open":
        subprocess.Popen(["explorer", str(WORKSPACE)])
        print(f"\n  {C.GREEN}\u2713{C.RESET} opened {WORKSPACE}\n")
        return True

    if command == "export":
        parts = value.split(maxsplit=1)
        source = parts[0] if parts else "."
        name = parts[1] if len(parts) > 1 else "auracode-export"
        result = export_to_downloads(source, name)
        print(f"\n  {C.GREEN}\u2713{C.RESET} {result}\n")
        return True

    print(f"  {C.DIM}Unknown command. Type /help{C.RESET}")
    return True


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
            print(f"  {C.MAGENTA}\u25B6{C.RESET} {C.CYAN}{tool}{C.RESET} {C.DIM}{detail}{C.RESET}")

        spinner = _start_spinner()
        try:
            tool_results = execute_actions(actions)
        finally:
            _stop_spinner()

        if tool_results.strip():
            preview_lines = tool_results.strip().split("\n")[:10]
            preview = "\n".join(preview_lines)
            if len(tool_results.strip().split("\n")) > 10:
                more = len(tool_results.strip().split("\n")) - 10
                preview += f"\n  {C.DIM}... {more} more lines{C.RESET}"
            print(f"  {preview}\n")


def _print_header():
    width = _term_width()
    print()
    print(_top_border())
    print(_box_line(f"{C.BOLD}{C.CYAN}AuraCode{C.RESET}  {C.DIM}v1.0{C.RESET}"))
    print(_box_line(f"{C.DIM}AI coding agent for your terminal{C.RESET}"))
    print(_separator())
    print(_box_line(f"  {C.DIM}Type a message or {C.CYAN}/help{C.RESET}{C.DIM} for commands{C.RESET}"))
    print(_bottom_border())
    print()


def main() -> None:
    chat_id = f"cli_{get_device_id()}_{uuid4().hex[:8]}"

    _print_header()

    while True:
        try:
            user_input = input(f"  {C.GREEN}\u25B6{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "/quit"}:
            print(f"\n  {C.DIM}bye{C.RESET}\n")
            break
        try:
            if handle_slash_command(user_input):
                continue
            run_agent_turn(user_input, chat_id)
        except KeyboardInterrupt:
            print(f"\n  {C.DIM}interrupted{C.RESET}\n")
            continue
        except Exception as exc:
            print(f"\n  {C.RED}\u2717 error:{C.RESET} {exc}\n")


if __name__ == "__main__":
    main()
