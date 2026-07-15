import base64
import json
import math
import os
import platform
import re
import struct
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information on any topic. Use for real-time data, news, documentation, and fact-checking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location including temperature, humidity, wind, and conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location"}
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute Python code in a sandboxed environment and return the output. Use for calculations, data processing, testing logic, generating content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current directory)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell/terminal command and return the output. Use for git, npm, pip, docker, and other CLI tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_image",
            "description": "Create an image using DALL-E API or generate SVG/HTML visual art.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the image to create"},
                    "size": {"type": "string", "description": "Image size: 1024x1024, 1792x1024, 1024x1792", "default": "1024x1024"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_code_project",
            "description": "Generate a complete, multi-file code project from a natural language description. Creates real files on disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the project to generate"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search uploaded documents for relevant information using semantic search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time in UTC and local timezone.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression. Supports arithmetic, exponents, trigonometry via math module.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and extract content from a URL. Supports webpages, APIs, raw files, JSON endpoints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files by name pattern or find files containing specific text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern or search text"},
                    "path": {"type": "string", "description": "Directory to search in (default: current directory)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Find and replace specific text in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "old_text": {"type": "string", "description": "Text to find and replace"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get system information: OS, Python version, installed packages, CPU, memory.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_project_from_prompt",
            "description": "Generate a complete multi-file project from a natural language prompt. Creates websites, APIs, apps, games, and more.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the project to build"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "Create a PDF document with formatted text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Text content for the PDF"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_excel",
            "description": "Create an Excel spreadsheet with structured data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Workbook title"},
                    "data": {"type": "string", "description": "JSON array of rows: [[col1, col2], [val1, val2]]"},
                },
                "required": ["title", "data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_zip",
            "description": "Create a ZIP archive containing multiple files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {"type": "string", "description": "JSON array of {path, content} objects"},
                    "name": {"type": "string", "description": "ZIP file name"},
                },
                "required": ["files", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_html",
            "description": "Generate a complete HTML page with inline CSS and JavaScript.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Description of the HTML page to create"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_markdown",
            "description": "Create a well-formatted Markdown document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Markdown content"},
                    "filename": {"type": "string", "description": "File name (optional)"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code",
            "description": "Analyze code for issues, complexity, and improvements. Returns a detailed report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to analyze"},
                    "language": {"type": "string", "description": "Programming language (auto-detected if not specified)"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_code",
            "description": "Explain how a piece of code works, line by line or section by section.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to explain"},
                    "detail_level": {"type": "string", "description": "brief, normal, or detailed", "default": "normal"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_code",
            "description": "Convert code from one programming language to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Source code to convert"},
                    "source_language": {"type": "string", "description": "Source programming language"},
                    "target_language": {"type": "string", "description": "Target programming language"},
                },
                "required": ["code", "source_language", "target_language"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Get git repository status, log, and diff information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Repository path (default: current directory)"},
                    "action": {"type": "string", "description": "Status, log, diff, or branches", "default": "status"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compress_text",
            "description": "Compress or summarize long text into a shorter version preserving key information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to compress/summarize"},
                    "target_length": {"type": "string", "description": "Target: short, medium, or detailed", "default": "medium"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "json_transform",
            "description": "Parse, validate, query, and transform JSON data. Supports jq-style queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "JSON string to process"},
                    "operation": {"type": "string", "description": "Operation: validate, query, format, minify, extract_keys"},
                    "query": {"type": "string", "description": "Query path or expression (for query operation)"},
                },
                "required": ["data", "operation"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool Executors
# ---------------------------------------------------------------------------

def execute_web_search(query: str) -> str:
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode("utf-8", errors="ignore")

        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html_content, re.DOTALL)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html_content, re.DOTALL)
        urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', html_content, re.DOTALL)

        results = []
        for i in range(min(8, len(titles))):
            title = re.sub(r"<[^>]+>", "", titles[i]).strip() if i < len(titles) else ""
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()[:200] if i < len(snippets) else ""
            url_text = re.sub(r"<[^>]+>", "", urls[i]).strip() if i < len(urls) else ""
            if title:
                results.append(f"{i+1}. **{title}**\n   {url_text}\n   {snippet}")

        if results:
            return f"Web search results for '{query}':\n\n" + "\n\n".join(results)
        return f"Web search for '{query}' completed but no structured results were extracted. Try refining the query."
    except Exception as exc:
        return f"Web search failed: {exc}"


def execute_weather(location: str) -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]
        city = (area.get("areaName") or [{"value": location}])[0].get("value", location)
        country = (area.get("country") or [{"value": ""}])[0].get("value", "")
        desc = (current.get("weatherDesc") or [{"value": "weather"}])[0].get("value", "weather")
        temp_c = current.get("temp_C", "")
        feels_c = current.get("FeelsLikeC", "")
        humidity = current.get("humidity", "")
        wind = current.get("windspeedKmph", "")
        visibility = current.get("visibility", "")
        pressure = current.get("pressure", "")

        forecast_lines = []
        for day in data.get("weather", [])[:3]:
            date = day.get("date", "")
            max_temp = day.get("maxtempC", "")
            min_temp = day.get("mintempC", "")
            forecast_lines.append(f"  {date}: {min_temp}°C - {max_temp}°C")

        result = f"Weather for {city}, {country}:\n"
        result += f"  Condition: {desc}\n"
        result += f"  Temperature: {temp_c}°C (feels like {feels_c}°C)\n"
        result += f"  Humidity: {humidity}%\n"
        result += f"  Wind: {wind} km/h\n"
        if visibility:
            result += f"  Visibility: {visibility} km\n"
        if pressure:
            result += f"  Pressure: {pressure} mb\n"
        if forecast_lines:
            result += f"\nForecast:\n" + "\n".join(forecast_lines)
        return result
    except Exception as exc:
        return f"Weather fetch failed for {location}: {exc}"


def execute_run_python(code: str) -> str:
    blocked = ["os.system", "subprocess", "shutil.rmtree", "__import__('os')"]
    for pattern in blocked:
        if pattern in code:
            return f"Blocked: code contains restricted pattern '{pattern}'."
    try:
        local_vars: dict[str, Any] = {}
        safe_builtins = {
            "print": print, "len": len, "range": range, "enumerate": enumerate,
            "zip": zip, "map": map, "filter": filter, "sorted": sorted,
            "reversed": reversed, "min": min, "max": max, "sum": sum,
            "abs": abs, "round": round, "int": int, "float": float, "str": str,
            "bool": bool, "list": list, "dict": dict, "set": set, "tuple": tuple,
            "type": type, "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
            "setattr": setattr, "repr": repr, "hash": hash, "id": id,
            "True": True, "False": False, "None": None,
            "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
            "KeyError": KeyError, "IndexError": IndexError, "AttributeError": AttributeError,
            "__import__": __import__,
        }
        exec(code, {"__builtins__": safe_builtins, "math": math, "json": json,
                     "re": re, "datetime": datetime, "timedelta": timedelta}, local_vars)
        output = local_vars.get("_result", local_vars.get("result", local_vars.get("output", "")))
        if not output:
            all_vars = {k: v for k, v in local_vars.items() if not k.startswith("_") and k not in {"__builtins__"}}
            output = str(all_vars) if all_vars else "Code executed successfully (no output variable)."
        return str(output)[:6000]
    except Exception as exc:
        return f"Python execution error: {exc}"


def execute_read_file(path: str) -> str:
    try:
        target = Path(path).resolve()
        if not target.is_file():
            return f"File not found: {path}"
        if target.stat().st_size > 200_000:
            return f"File too large ({target.stat().st_size} bytes). Read a smaller file."
        content = target.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        total = len(lines)
        if total > 300:
            preview = "\n".join(lines[:300])
            return f"{preview}\n\n... [{total - 300} more lines] (showing first 300 of {total} lines)"
        return content[:12000]
    except Exception as exc:
        return f"Error reading file: {exc}"


def execute_write_file(path: str, content: str) -> str:
    try:
        target = Path(path).resolve()
        if ".." in target.parts:
            return "Unsafe path: no parent traversal allowed."
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"File written successfully: {path} ({len(content)} bytes, {content.count(chr(10))} lines)"
    except Exception as exc:
        return f"Error writing file: {exc}"


def execute_list_files(path: str = ".") -> str:
    try:
        target = Path(path).resolve()
        if not target.is_dir():
            return f"Directory not found: {path}"
        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines = []
        total_size = 0
        for entry in entries[:80]:
            if entry.name.startswith(".") and entry.name not in {".gitignore", ".env.example"}:
                continue
            if entry.name in {"__pycache__", "node_modules", ".venv", "venv"}:
                continue
            prefix = "[DIR] " if entry.is_dir() else "      "
            size = entry.stat().st_size if entry.is_file() else 0
            total_size += size
            size_str = f" ({self_size_format(size)})" if entry.is_file() else ""
            lines.append(f"{prefix}{entry.name}{size_str}")
        footer = f"\n{len(entries)} items" if entries else "Directory is empty"
        if total_size > 0:
            footer += f" ({self_size_format(total_size)} total)"
        return "\n".join(lines) + footer
    except Exception as exc:
        return f"Error listing files: {exc}"


def self_size_format(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf ~", "rmdir /s", "del /s /q", "format ", "shutdown",
    "mkfs", "git reset --hard", "git push --force", "git clean -fd",
]


def execute_command(command: str) -> str:
    lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in lower:
            return f"Blocked: destructive command '{blocked}' is not allowed."
    try:
        timeout_val = 60
        if any(kw in lower for kw in ["npm install", "pip install", "yarn", "cargo build"]):
            timeout_val = 120
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_val,
            cwd=Path.cwd(),
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = stdout or stderr
        if not output:
            return f"Command completed with exit code {result.returncode}."
        lines = output.split("\n")
        if len(lines) > 60:
            lines = lines[:30] + ["... truncated ..."] + lines[-20:]
        output = "\n".join(lines)
        if len(output) > 6000:
            output = output[:3000] + "\n... [truncated] ...\n" + output[-2500:]
        return output
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout_val}s."
    except Exception as exc:
        return f"Command execution failed: {exc}"


def execute_create_image(prompt: str, size: str = "1024x1024") -> str:
    from .config import get_settings
    settings = get_settings()
    if settings.openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.images.generate(model="dall-e-3", prompt=prompt, size=size, quality="standard", n=1)
            return f"Image generated successfully.\nURL: {response.data[0].url}\nRevised prompt: {response.data[0].revised_prompt}"
        except Exception as exc:
            return f"DALL-E image generation failed: {exc}. Falling back to SVG generation."
    return f"No OpenAI API key configured for DALL-E. To generate real images, add OPENAI_API_KEY to your .env file.\nSVG fallback: Use the artifact system to create an SVG based on '{prompt}'."


def execute_calculate(expression: str) -> str:
    allowed_chars = set("0123456789+-*/.() %^")
    if not all(c in allowed_chars for c in expression):
        return "Invalid characters in expression."
    try:
        safe_expr = expression.replace("^", "**")
        result = eval(safe_expr, {"__builtins__": {}}, {"math": math})
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                return str(int(result))
            return f"{result:.10g}"
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


def execute_get_current_time() -> str:
    now_utc = datetime.utcnow()
    now_local = datetime.now()
    weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return (
        f"UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')} ({weekday[now_utc.weekday()]})\n"
        f"Local: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')} ({weekday[now_local.weekday()]})"
    )


def execute_fetch_url(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Aurine AI Assistant)"})
        with urllib.request.urlopen(req, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read().decode("utf-8", errors="ignore")
            if "json" in content_type:
                try:
                    parsed = json.loads(data)
                    return json.dumps(parsed, indent=2, ensure_ascii=False)[:10000]
                except json.JSONDecodeError:
                    pass
            if any(t in content_type for t in ["html", "text"]) or url.endswith((".html", ".txt", ".md", ".json", ".xml", ".csv")):
                text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", data, flags=re.IGNORECASE)
                text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:10000]
            return f"Fetched {len(data)} bytes from {url} (Content-Type: {content_type})."
    except Exception as exc:
        return f"URL fetch failed for {url}: {exc}"


def execute_search_files(pattern: str, path: str = ".") -> str:
    try:
        target = Path(path).resolve()
        if not target.is_dir():
            return f"Directory not found: {path}"
        matches = []
        pattern_lower = pattern.lower()
        for file in target.rglob("*"):
            if file.is_file() and len(matches) < 50:
                if pattern_lower in file.name.lower() or pattern_lower in file.suffix.lower():
                    matches.append(str(file.relative_to(target)))
        if not matches:
            for file in target.rglob("*"):
                if file.is_file() and len(matches) < 30:
                    try:
                        content = file.read_text(encoding="utf-8", errors="ignore")[:20000]
                        if pattern_lower in content.lower():
                            matches.append(str(file.relative_to(target)))
                    except (OSError, PermissionError):
                        continue
        return "\n".join(matches[:50]) if matches else f"No files found matching '{pattern}'."
    except Exception as exc:
        return f"File search failed: {exc}"


def execute_replace_in_file(path: str, old_text: str, new_text: str) -> str:
    try:
        target = Path(path).resolve()
        if not target.is_file():
            return f"File not found: {path}"
        content = target.read_text(encoding="utf-8", errors="ignore")
        count = content.count(old_text)
        if count == 0:
            return f"Text not found in {path}."
        new_content = content.replace(old_text, new_text)
        target.write_text(new_content, encoding="utf-8")
        return f"Replaced {count} occurrence(s) in {path}."
    except Exception as exc:
        return f"Replace failed: {exc}"


def execute_get_system_info() -> str:
    import os as _os
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": _os.cpu_count(),
        "current_dir": str(Path.cwd()),
        "hostname": platform.node(),
    }
    try:
        import shutil
        for cmd in ["git", "node", "npm", "docker", "python"]:
            version = shutil.which(cmd)
            if version:
                info[f"{cmd}_available"] = "Yes"
    except Exception:
        pass
    return "\n".join(f"{k}: {v}" for k, v in info.items())


def execute_generate_project_from_prompt(prompt: str) -> str:
    try:
        from .codegen import generate_project
        project = generate_project(prompt)
        return (
            f"Project created: {project['name']}\n"
            f"ID: {project['id']}\n"
            f"Files: {len(project.get('files', []))}\n"
            f"Description: {project.get('description', '')}\n"
            f"Run: {project.get('run_instructions', '')}"
        )
    except Exception as exc:
        return f"Project generation failed: {exc}"


def execute_create_pdf(title: str, content: str) -> str:
    try:
        from .artifacts import create_pdf as _create_pdf
        from pathlib import Path as _Path
        import tempfile
        folder = _Path(tempfile.mkdtemp())
        files = _create_pdf(folder, f"{title}\n\n{content}")
        return f"PDF created: {files[0]['name']} in {folder}"
    except Exception as exc:
        return f"PDF creation failed: {exc}"


def execute_create_excel(title: str, data: str) -> str:
    try:
        from .artifacts import create_excel as _create_excel
        from pathlib import Path as _Path
        import tempfile
        folder = _Path(tempfile.mkdtemp())
        files = _create_excel(folder, f"{title}\n\n{data}")
        return f"Excel created: {files[0]['name']} in {folder}"
    except Exception as exc:
        return f"Excel creation failed: {exc}"


def execute_create_zip(files_json: str, name: str) -> str:
    try:
        files = json.loads(files_json) if isinstance(files_json, str) else files_json
        from pathlib import Path as _Path
        import tempfile
        import zipfile
        folder = _Path(tempfile.mkdtemp())
        zip_path = folder / f"{name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for f in files:
                archive.writestr(f.get("path", "file.txt"), f.get("content", ""))
        return f"ZIP created: {zip_path} ({len(files)} files)"
    except Exception as exc:
        return f"ZIP creation failed: {exc}"


def execute_generate_html(prompt: str) -> str:
    try:
        from .artifacts import create_html_file as _create_html
        from pathlib import Path as _Path
        import tempfile
        folder = _Path(tempfile.mkdtemp())
        files = _create_html(folder, prompt)
        return f"HTML created: {files[0]['name']} in {folder}"
    except Exception as exc:
        return f"HTML creation failed: {exc}"


def execute_create_markdown(title: str, content: str, filename: str = "") -> str:
    try:
        from pathlib import Path as _Path
        import tempfile
        folder = _Path(tempfile.mkdtemp())
        fname = filename or f"{title.lower().replace(' ', '-')}.md"
        md_content = f"# {title}\n\n{content}"
        path = folder / fname
        path.write_text(md_content, encoding="utf-8")
        return f"Markdown created: {path} ({len(md_content)} chars)"
    except Exception as exc:
        return f"Markdown creation failed: {exc}"


def execute_analyze_code(code: str, language: str = "") -> str:
    lines = code.split("\n")
    total_lines = len(lines)
    blank_lines = sum(1 for l in lines if not l.strip())
    comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*", "<!--")))
    code_lines = total_lines - blank_lines - comment_lines

    if not language:
        ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java",
                   ".c": "c", ".cpp": "cpp", ".rs": "rust", ".go": "go"}
        for ext, lang in ext_map.items():
            if ext in code.lower():
                language = lang
                break

    issues = []
    warnings = []
    if "TODO" in code:
        warnings.append("Contains TODO comments")
    if "FIXME" in code:
        issues.append("Contains FIXME markers - needs attention")
    if "except:" in code or "catch {}" in code:
        warnings.append("Broad exception handling detected")
    if "password" in code.lower() and "=" in code:
        issues.append("Potential hardcoded password detected")
    if "eval(" in code:
        warnings.append("eval() usage detected - potential security risk")
    if code.count("\n") > 500:
        warnings.append("File is very long ({code_lines} lines) - consider splitting")

    report = f"Code Analysis Report:\n"
    report += f"  Language: {language or 'unknown'}\n"
    report += f"  Total lines: {total_lines}\n"
    report += f"  Code lines: {code_lines}\n"
    report += f"  Comments: {comment_lines}\n"
    report += f"  Blank: {blank_lines}\n"
    if issues:
        report += f"\nIssues ({len(issues)}):\n" + "\n".join(f"  - {i}" for i in issues)
    if warnings:
        report += f"\nWarnings ({len(warnings)}):\n" + "\n".join(f"  - {w}" for w in warnings)
    if not issues and not warnings:
        report += "\nNo significant issues found."
    return report


def execute_explain_code(code: str, detail_level: str = "normal") -> str:
    lines = code.strip().split("\n")
    explanations = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            explanations.append(f"Line {i}: Comment - {stripped.lstrip('#').strip()}")
        elif stripped.startswith("def ") or stripped.startswith("function "):
            explanations.append(f"Line {i}: Function definition - {stripped}")
        elif stripped.startswith("class "):
            explanations.append(f"Line {i}: Class definition - {stripped}")
        elif "import " in stripped:
            explanations.append(f"Line {i}: Import statement - {stripped}")
        elif stripped.startswith("return "):
            explanations.append(f"Line {i}: Returns {stripped[7:]}")
        elif stripped.startswith("if ") or stripped.startswith("elif ") or stripped.startswith("else"):
            explanations.append(f"Line {i}: Conditional - {stripped}")
        elif stripped.startswith("for ") or stripped.startswith("while "):
            explanations.append(f"Line {i}: Loop - {stripped}")
        elif detail_level == "detailed" and stripped:
            explanations.append(f"Line {i}: {stripped}")
    if not explanations:
        return "No explainable lines found in the provided code."
    return "Code Explanation:\n" + "\n".join(explanations[:50])


def execute_convert_code(code: str, source_language: str, target_language: str) -> str:
    return (
        f"Code conversion from {source_language} to {target_language} requested.\n"
        f"The AI will handle the actual conversion using its language model capabilities.\n"
        f"Source code length: {len(code)} chars, {code.count(chr(10))} lines."
    )


def execute_git_status(path: str = ".", action: str = "status") -> str:
    try:
        action = action.lower().strip()
        if action == "log":
            cmd = f"git -C \"{path}\" log --oneline -15"
        elif action == "diff":
            cmd = f"git -C \"{path}\" diff --stat"
        elif action == "branches":
            cmd = f"git -C \"{path}\" branch -a"
        else:
            cmd = f"git -C \"{path}\" status --short"
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=15)
        output = (result.stdout + result.stderr).strip()
        return output or f"Git {action}: no output."
    except Exception as exc:
        return f"Git command failed: {exc}"


def execute_compress_text(text: str, target_length: str = "medium") -> str:
    max_lens = {"short": 200, "medium": 500, "detailed": 1000}
    max_len = max_lens.get(target_length, 500)
    words = text.split()
    if len(words) * 5 <= max_len:
        return text
    sentences = re.split(r'[.!?]+', text)
    important = sorted(sentences, key=lambda s: len(s.split()), reverse=True)
    result = ". ".join(s.strip() for s in important if s.strip())[:max_len]
    return result + "..." if len(result) >= max_len else result


def execute_json_transform(data: str, operation: str, query: str = "") -> str:
    try:
        parsed = json.loads(data)
        if operation == "validate":
            return f"Valid JSON. Type: {type(parsed).__name__}, Length: {len(parsed) if hasattr(parsed, '__len__') else 'N/A'}"
        elif operation == "format":
            return json.dumps(parsed, indent=2, ensure_ascii=False)[:10000]
        elif operation == "minify":
            return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        elif operation == "extract_keys":
            if isinstance(parsed, dict):
                return json.dumps(list(parsed.keys()), indent=2)
            elif isinstance(parsed, list):
                return f"Array with {len(parsed)} items"
            return str(type(parsed))
        elif operation == "query":
            if not query:
                return "Query path required for query operation."
            parts = query.strip(".").split(".")
            current = parsed
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    current = current[int(part)]
                else:
                    return f"Cannot navigate to '{part}' in current value."
            return json.dumps(current, indent=2, ensure_ascii=False)[:10000] if not isinstance(current, str) else current
        return f"Unknown operation: {operation}. Use: validate, format, minify, extract_keys, query"
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"


def _search_documents_tool(query: str) -> str:
    try:
        from .rag import retrieve_context
        context, sources = retrieve_context(query, limit=5)
        if not context:
            return "No uploaded documents found. Upload files via the File upload button first."
        parts = []
        for s in sources:
            parts.append(f"[{s['source']} chunk {s['chunk']}] (relevance: {s['score']:.2f})")
        return f"Found {len(sources)} relevant chunks:\n" + "\n".join(parts) + "\n\n" + context[:6000]
    except Exception as exc:
        return f"Document search failed: {exc}"


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

TOOL_EXECUTORS = {
    "web_search": lambda args: execute_web_search(args.get("query", "")),
    "get_weather": lambda args: execute_weather(args.get("location", "Mumbai")),
    "run_python": lambda args: execute_run_python(args.get("code", "")),
    "read_file": lambda args: execute_read_file(args.get("path", "")),
    "write_file": lambda args: execute_write_file(args.get("path", ""), args.get("content", "")),
    "list_files": lambda args: execute_list_files(args.get("path", ".")),
    "execute_command": lambda args: execute_command(args.get("command", "")),
    "create_image": lambda args: execute_create_image(args.get("prompt", ""), args.get("size", "1024x1024")),
    "calculate": lambda args: execute_calculate(args.get("expression", "")),
    "get_current_time": lambda args: execute_get_current_time(),
    "fetch_url": lambda args: execute_fetch_url(args.get("url", "")),
    "search_files": lambda args: execute_search_files(args.get("pattern", ""), args.get("path", ".")),
    "replace_in_file": lambda args: execute_replace_in_file(args.get("path", ""), args.get("old_text", ""), args.get("new_text", "")),
    "get_system_info": lambda args: execute_get_system_info(),
    "generate_project_from_prompt": lambda args: execute_generate_project_from_prompt(args.get("prompt", "")),
    "search_documents": lambda args: _search_documents_tool(args.get("query", "")),
    "generate_code_project": lambda args: execute_generate_project_from_prompt(args.get("prompt", "")),
    "create_pdf": lambda args: execute_create_pdf(args.get("title", ""), args.get("content", "")),
    "create_excel": lambda args: execute_create_excel(args.get("title", ""), args.get("data", "[]")),
    "create_zip": lambda args: execute_create_zip(args.get("files", "[]"), args.get("name", "archive")),
    "generate_html": lambda args: execute_generate_html(args.get("prompt", "")),
    "create_markdown": lambda args: execute_create_markdown(args.get("title", ""), args.get("content", ""), args.get("filename", "")),
    "analyze_code": lambda args: execute_analyze_code(args.get("code", ""), args.get("language", "")),
    "explain_code": lambda args: execute_explain_code(args.get("code", ""), args.get("detail_level", "normal")),
    "convert_code": lambda args: execute_convert_code(args.get("code", ""), args.get("source_language", ""), args.get("target_language", "")),
    "git_status": lambda args: execute_git_status(args.get("path", "."), args.get("action", "status")),
    "compress_text": lambda args: execute_compress_text(args.get("text", ""), args.get("target_length", "medium")),
    "json_transform": lambda args: execute_json_transform(args.get("data", "{}"), args.get("operation", "validate"), args.get("query", "")),
}


def execute_tool(tool_name: str, arguments: dict) -> str:
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return f"Unknown tool: {tool_name}"
    try:
        return executor(arguments)
    except Exception as exc:
        return f"Tool execution error ({tool_name}): {exc}"


def has_tool_support(model_config: dict | None = None) -> bool:
    if not model_config:
        return False
    provider = str(model_config.get("provider", "")).lower()
    model = str(model_config.get("model", "")).lower()
    openai_compat = {
        "openai", "codex", "anthropic", "groq", "openrouter",
        "mistral", "nvidia", "fireworks", "cerebras", "sambanova", "deepseek",
    }
    if provider in openai_compat:
        return True
    if provider in {"aurine", "ollama"}:
        return "qwen" in model or "llama" in model or "mistral" in model or "deepseek" in model or "codestral" in model
    return False
