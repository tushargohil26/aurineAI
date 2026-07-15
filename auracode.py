import json
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime
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


SYSTEM_PROMPT = """
You are AuraCode, a terminal coding agent running on the user's desktop.
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
- Your message must be a useful answer, not filler. Do not include irrelevant or invalid information.
- Do not try to run python app.py unless an app.py file really exists.
- For this FastAPI assistant, run python -m uvicorn app.main:app --reload --port 8000.
- For generated static websites, do not run Python. Save HTML/CSS/JS files inside generated_projects/<project-name>/, never directly into static/ unless the user explicitly asks to modify this AI assistant app.
- If the user asks to put files in Downloads, use export_to_downloads after creating the files in the workspace.
"""


def safe_path(path: str) -> Path:
    candidate = (WORKSPACE / path).resolve()
    if not str(candidate).startswith(str(WORKSPACE)):
        raise ValueError("Path escapes workspace.")
    return candidate


IGNORE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache", "vector_store.sqlite3"}


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
            rel = entry.relative_to(WORKSPACE)
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
    return "\n".join(lines[:150]) + ("\n... more files" if len(lines) > 150 else "") or "No files found."


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
        command,
        cwd=WORKSPACE,
        shell=True,
        text=True,
        capture_output=True,
        timeout=60,
    )
    output = (result.stdout + result.stderr).strip()
    return output[:30000] or f"Command exited with code {result.returncode}."


def command_exists(name: str) -> bool:
    return bool(shutil.which(name))


def run_tool_command(command: list[str], timeout: int = 12) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=WORKSPACE,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
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
            return "Git: Missing. Install Git and add it to PATH."
        return "Git: Ready\n" + run_tool_command(["git", "--version"]) + "\n" + run_tool_command(["git", "status", "--short"])
    if plugin in {"github", "gh"}:
        if not command_exists("gh"):
            return "GitHub: Missing. Install GitHub CLI first: https://cli.github.com/"
        return "GitHub:\n" + run_tool_command(["gh", "auth", "status"])
    if plugin in {"vscode", "code"}:
        if not command_exists("code"):
            return "VS Code: Missing. Install VS Code and enable the code command in PATH."
        return "VS Code: Ready\n" + run_tool_command(["code", "--version"])
    if plugin in {"sql", "sqlite"}:
        db = WORKSPACE / "vector_store.sqlite3"
        return f"SQLite: {'Ready' if db.exists() else 'Database will be created on first run'}\nPath: {db}"
    if plugin in {"terminal", "powershell"}:
        return "Terminal: Ready\n" + run_tool_command(["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"])
    if plugin in {"codebuilder", "builder", "files", "sites", "media"}:
        return f"{plugin}: Built into Aurine and available in the web app."
    return "Unknown plugin. Use /plugins."


def connect_plugin(plugin: str) -> str:
    plugin = plugin.lower().strip()
    if plugin in {"github", "gh"}:
        if not command_exists("gh"):
            return "GitHub CLI is not installed. Install gh first, then run /connect github."
        subprocess.Popen(
            ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "gh auth login"],
            cwd=WORKSPACE,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return "Opened GitHub login terminal. Finish gh auth login there, then run /plugin github."
    if plugin in {"vscode", "code"}:
        if not command_exists("code"):
            return "VS Code 'code' command is not in PATH."
        subprocess.Popen(["code", "."], cwd=WORKSPACE)
        return "Opened Aurine workspace in VS Code."
    if plugin in {"terminal", "powershell"}:
        subprocess.Popen(
            ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "Write-Host 'Aurine terminal connected'; Set-Location -LiteralPath ."],
            cwd=WORKSPACE,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return "Opened connected PowerShell terminal."
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
                    result = "Skipped python app.py because app.py does not exist. For this app use: python -m uvicorn app.main:app --reload --port 8000"
                else:
                    result = run_command(command)
            elif tool == "export_to_downloads":
                result = export_to_downloads(action.get("source", "."), action.get("name", "auracode-export"))
            else:
                result = f"Unknown tool: {tool}"
        except Exception as exc:
            result = f"Error: {exc}"
        results.append(f"{_dim('[' + tool + ']')} {result}")
    return "\n".join(results)


def handle_builtin(user_input: str) -> bool:
    normalized = user_input.strip().lower()
    targets = {
        "open app": WORKSPACE,
        "open project": WORKSPACE / "generated_projects",
        "open projects": WORKSPACE / "generated_projects",
        "open generated": WORKSPACE / "generated_projects",
        "open aurashine": WORKSPACE / "generated_projects",
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
  {_bold('Commands')}
  {_dim('/files')} [path]         {_dim('list workspace files')}
  {_dim('/read')}  <path>         {_dim('read a file')}
  {_dim('/run')}   <command>      {_dim('run a safe shell command')}
  {_dim('/open')}                  {_dim('open workspace folder')}
  {_dim('/export')} [path] [name] {_dim('export to Downloads')}
  {_dim('/plugins')}               {_dim('list available plugins')}
  {_dim('/history')}               {_dim('view past chats')}
  {_dim('/device')}                {_dim('show device info')}
  {_dim('/quit')}                  {_dim('exit AuraCode')}
""")
        return True
    if command == "plugins":
        print(f"\n  {_bold('Plugins')}: git, github, vscode, sql, terminal, codebuilder, files, sites, media\n")
        return True
    if command == "plugin":
        print(f"\n  {plugin_status(value or '')}\n")
        return True
    if command == "connect":
        if not value:
            print(f"  {_dim('Usage: /connect github|vscode|terminal')}")
        else:
            print(f"\n  {connect_plugin(value)}\n")
        return True
    if command in {"files", "ls"}:
        print(f"\n  {_bold('Files')}\n")
        for line in (list_files(value or ".") or "No files found.").split("\n"):
            print(f"    {line}")
        print()
        return True
    if command == "read":
        if not value:
            print(f"  {_dim('Usage: /read <relative-file-path>')}")
        else:
            content = read_file(value)
            print(f"\n  {_bold(value)}\n")
            for line in content.split("\n"):
                print(f"    {line}")
            print()
        return True
    if command == "run":
        if not value:
            print(f"  {_dim('Usage: /run <command>')}")
        else:
            result = run_command(value)
            print(f"\n  {_cyan('$')} {value}\n")
            for line in result.split("\n"):
                print(f"    {line}")
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
        target.mkdir(parents=True, exist_ok=True)
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
    print(f"  {_dim('Unknown command. Type /help.')}")
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
            "content": f"Workspace: {WORKSPACE}\nTool results:\n{tool_results}\n\nUser request: {user_input}",
        })
    else:
        messages.append({"role": "user", "content": f"Workspace: {WORKSPACE}\n\nUser request: {user_input}"})

    content = chat_completion(messages, temperature=0.1, json_mode=True)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "message": "I could not parse the model response as tool JSON, so I did not run any unsafe action. Please try the request again with the exact file or app you want changed.",
            "actions": [],
        }


def _print_bordered(text: str, color: str = "36") -> None:
    lines = text.split("\n")
    width = max(len(line) for line in lines) if lines else 40
    print(f"\033[{color}m{lines[0]}\033[0m")
    for line in lines[1:]:
        print(f"  \033[{color}m{line}\033[0m")


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


def run_agent_turn(user_input: str, chat_id: str) -> None:
    extract_facts_from_message(user_input)
    store_chat_message(chat_id, "user", user_input)
    history = get_chat_history(chat_id, limit=30)

    tool_results = ""
    for _ in range(5):
        response = ask_agent(user_input, tool_results, history)
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
            print(f"  {_cyan('>')}{_dim(tool)} {_dim(str(detail))}")

        tool_results = execute_actions(actions)
        if tool_results.strip():
            preview_lines = tool_results.strip().split("\n")[:15]
            preview = "\n".join(preview_lines)
            if len(tool_results.strip().split("\n")) > 15:
                preview += f"\n  {_dim('... ' + str(len(tool_results.strip().split(chr(10))) - 15) + ' more lines')}"
            print(f"  {_dim(preview)}\n")


def main() -> None:
    device_id = get_device_id()
    user_id = get_user_id()
    device_name = get_device_name()
    chat_id = f"cli_{device_id}_{uuid4().hex[:8]}"

    print()
    print(f"  {_bold(_cyan('AuraCode'))}  {_dim('terminal agent')}")
    print(f"  {_dim(device_name)}  {_dim('workspace:')} {_dim(str(WORKSPACE))}")
    print(f"  {_dim('/help')} commands  {_dim('/quit')} exit")
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
            print(f"\n  {_dim('goodbye')}\n")
            break
        if user_input.lower() == "/history":
            chats = get_all_chats()
            if chats:
                print(f"\n  {_bold('Past chats')} ({len(chats)} total):")
                for c in chats[:10]:
                    print(f"    {_dim(c['chat_id'][:16])}  {_dim(str(c['message_count']))} messages  {c['last_message'][:30]}")
            else:
                print("  No past chats yet.")
            print()
            continue
        if user_input.lower() == "/device":
            info = {
                "device_id": device_id,
                "user_id": user_id,
                "device_name": device_name,
                "facts": len(recall_facts()),
                "patterns": len(get_learned_patterns()),
            }
            print(f"\n  {json.dumps(info, indent=4)}\n")
            continue
        try:
            if handle_builtin(user_input):
                continue
            if handle_slash_command(user_input):
                continue
            run_agent_turn(user_input, chat_id)
        except Exception as exc:
            print(f"\n  {_red('error:')} {exc}\n")


if __name__ == "__main__":
    main()





