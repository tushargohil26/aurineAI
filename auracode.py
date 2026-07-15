import json
import shutil
import subprocess
from pathlib import Path

from app.llm import chat_completion


WORKSPACE = Path.cwd().resolve()


SYSTEM_PROMPT = """
You are AuraCode, a terminal coding agent running on the user's desktop.
You can inspect files, write files, and run shell commands through tools.
Always respond with valid JSON:
{
  "message": "short explanation for user",
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
- Inspect the workspace with list_files before guessing filenames.
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


def list_files(path: str = ".") -> str:
    root = safe_path(path)
    if not root.exists():
        return "Path does not exist."
    files = []
    for item in root.rglob("*"):
        if ".venv" in item.parts or "__pycache__" in item.parts:
            continue
        if item.is_file():
            files.append(str(item.relative_to(WORKSPACE)))
        if len(files) >= 200:
            files.append("... truncated ...")
            break
    return "\n".join(files) or "No files found."


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
        results.append(f"[{tool}]\n{result}")
    return "\n\n".join(results)


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
    print(f"Opened: {target}")
    return True


def handle_slash_command(user_input: str) -> bool:
    if not user_input.startswith("/"):
        return False
    command, _, value = user_input[1:].partition(" ")
    command = command.lower().strip()
    value = value.strip()
    if command in {"help", "?"}:
        print(
            """
Slash commands:
  /help                 Show commands
  /files [path]         List workspace files
  /read <path>          Read a file
  /run <command>        Run a safe shell command
  /open                 Open this workspace folder
  /projects             Open generated_projects
  /downloads            Open Downloads
  /export [path] [name] Export a file/folder to Downloads
  /plugins              List real plugin names
  /plugin <name>        Check Git/GitHub/VS Code/SQL/Terminal status
  /connect <name>       Start real connect flow for GitHub/VS Code/Terminal
"""
        )
        return True
    if command == "plugins":
        print("Plugins: git, github, vscode, sql, terminal, codebuilder, files, sites, media")
        return True
    if command == "plugin":
        print(plugin_status(value or ""))
        return True
    if command == "connect":
        if not value:
            print("Usage: /connect github|vscode|terminal")
        else:
            print(connect_plugin(value))
        return True
    if command in {"files", "ls"}:
        print(list_files(value or "."))
        return True
    if command == "read":
        if not value:
            print("Usage: /read <relative-file-path>")
        else:
            print(read_file(value))
        return True
    if command == "run":
        if not value:
            print("Usage: /run <command>")
        else:
            print(run_command(value))
        return True
    if command == "open":
        subprocess.Popen(["explorer", str(WORKSPACE)])
        print(f"Opened: {WORKSPACE}")
        return True
    if command in {"projects", "generated"}:
        target = WORKSPACE / "generated_projects"
        target.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(target)])
        print(f"Opened: {target}")
        return True
    if command == "downloads":
        target = Path.home() / "Downloads"
        target.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(target)])
        print(f"Opened: {target}")
        return True
    if command == "export":
        parts = value.split(maxsplit=1)
        source = parts[0] if parts else "."
        name = parts[1] if len(parts) > 1 else "auracode-export"
        print(export_to_downloads(source, name))
        return True
    print("Unknown slash command. Type /help.")
    return True


def ask_agent(user_input: str, tool_results: str = "") -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Workspace: {WORKSPACE}\nTool results:\n{tool_results}\n\nUser request: {user_input}",
        },
    ]
    content = chat_completion(messages, temperature=0.1, json_mode=True)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "message": "I could not parse the model response as tool JSON, so I did not run any unsafe action. Please try the request again with the exact file or app you want changed.",
            "actions": [],
        }


def run_agent_turn(user_input: str) -> None:
    tool_results = ""
    for _ in range(5):
        response = ask_agent(user_input, tool_results)
        message = response.get("message", "")
        if message:
            print(message)
        actions = response.get("actions", [])
        if not actions:
            return
        tool_results = execute_actions(actions)
        print(tool_results)


def main() -> None:
    print(r"""
    ___                     ______          __
   /   |  __  __________ _ / ____/___  ____/ /__
  / /| | / / / / ___/ __ `/ /   / __ \/ __  / _ \
 / ___ |/ /_/ / /  / /_/ / /___/ /_/ / /_/ /  __/
/_/  |_|\__,_/_/   \__,_/\____/\____/\__,_/\___/
""")
    print("AuraCode terminal agent")
    print(f"Workspace: {WORKSPACE}")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("auracode> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        try:
            if handle_builtin(user_input):
                continue
            if handle_slash_command(user_input):
                continue
            run_agent_turn(user_input)
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()





