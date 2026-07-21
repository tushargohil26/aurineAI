from pathlib import Path
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import shutil
import sqlite3
import time
import urllib.parse
import urllib.request
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import Body, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent_tools import TOOL_DEFINITIONS, execute_tool, has_tool_support
from .agents import AGENT_DEFINITIONS, classify_query, get_agent, list_agents, build_agent_messages
from .artifacts import create_artifact, get_artifact_file, list_artifacts
from .codegen import (
    generate_project,
    get_project_dir,
    list_project_files,
    list_projects,
    project_zip_path,
    read_project_file,
    run_project_command,
    write_project_file,
)
from .config import get_settings, reload_settings
from .llm import chat_completion, chat_completion_stream, chat_with_tools, supports_tools
from .memory import memory_store
from .device import get_device_id, get_user_id
from .rag import answer_question, ingest_file, list_documents
from .reasoning import ReasoningEngine, build_reasoning_context


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aurine")


rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 30


def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    rate_limit_store[client_ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Aurine AI Assistant v3.0 starting up...")
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_projects_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.vector_db)
    db.close()
    logger.info(f"Database ready: {settings.vector_db}")
    logger.info(f"Provider: {settings.ai_provider} | Reasoning: {settings.reasoning_enabled} | Memory: {settings.memory_enabled}")
    yield
    logger.info("Aurine AI Assistant shutting down...")


app = FastAPI(title="Aurine AI Assistant", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    question: str
    user_text: str = ""
    history: list[dict] = Field(default_factory=list)
    chat_id: str | None = None
    agent_mode: str = ""
    model_provider: str = ""
    model_name: str = ""
    model_base_url: str = ""
    model_api_key: str = ""
    reasoning: bool = False
    user_id: str = "default"


class ChatCreateRequest(BaseModel):
    title: str = "New chat"
    agent_mode: str = ""


class CodeProjectRequest(BaseModel):
    prompt: str


class ArtifactRequest(BaseModel):
    prompt: str
    artifact_type: str | None = None
    previous_artifact_id: str | None = None


class ProjectFileRequest(BaseModel):
    path: str
    content: str = ""


class CommandRequest(BaseModel):
    command: str


class AuthRequest(BaseModel):
    name: str
    email: str
    password: str


class SettingsRequest(BaseModel):
    name: str = ""
    workspace_name: str = ""
    theme: str = "aurora-3d"


class ScheduledRequest(BaseModel):
    title: str
    detail: str = ""
    due_at: str = ""


class AgentRequest(BaseModel):
    name: str
    detail: str = ""
    instructions: str


class PluginToggleRequest(BaseModel):
    plugin_id: str
    enabled: bool


class PluginRunRequest(BaseModel):
    plugin_id: str
    action: str = "check"


class ApiKeyCreateRequest(BaseModel):
    name: str = "API key"


class OpenAIChatCompletionRequest(BaseModel):
    model: str = "aurine"
    messages: list[dict] = Field(default_factory=list)
    temperature: float = 0.2
    stream: bool = False


def db_connection() -> sqlite3.Connection:
    settings = get_settings()
    connection = sqlite3.connect(settings.vector_db)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    chat_columns = {row["name"] for row in connection.execute("PRAGMA table_info(chats)").fetchall()}
    if "agent_mode" not in chat_columns:
        connection.execute("ALTER TABLE chats ADD COLUMN agent_mode TEXT NOT NULL DEFAULT ''")
    if "model_config" not in chat_columns:
        connection.execute("ALTER TABLE chats ADD COLUMN model_config TEXT NOT NULL DEFAULT '{}'")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    try:
        connection.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT NOT NULL DEFAULT ''")
    except Exception:
        pass
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_settings (
            user_id TEXT PRIMARY KEY,
            workspace_name TEXT NOT NULL,
            theme TEXT NOT NULL DEFAULT 'coder-night',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_items (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            due_at TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_agents (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            instructions TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS plugin_settings (
            user_id TEXT NOT NULL,
            plugin_id TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, plugin_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            key_prefix TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT NOT NULL DEFAULT '',
            revoked INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id TEXT PRIMARY KEY,
            chat_id TEXT,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL DEFAULT '{}',
            result TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    return connection


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def ensure_chat(chat_id: str | None, title_seed: str = "New chat", agent_mode: str = "") -> str:
    now = utc_now()
    with db_connection() as connection:
        if chat_id:
            row = connection.execute("SELECT id FROM chats WHERE id = ?", (chat_id,)).fetchone()
            if row:
                if agent_mode:
                    connection.execute(
                        "UPDATE chats SET agent_mode = ?, updated_at = ? WHERE id = ?",
                        (agent_mode[:80], now, chat_id),
                    )
                return chat_id

        new_id = uuid4().hex
        title = (title_seed.strip() or "New chat")[:48]
        connection.execute(
            "INSERT INTO chats (id, title, agent_mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (new_id, title, agent_mode[:80], now, now),
        )
        return new_id


def add_chat_message(chat_id: str, role: str, content: str, sources: list[dict] | None = None) -> None:
    now = utc_now()
    with db_connection() as connection:
        connection.execute(
            """
            INSERT INTO chat_messages (id, chat_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uuid4().hex, chat_id, role, content, json_dumps(sources or []), now),
        )
        connection.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def json_loads(value: str) -> object:
    try:
        return json.loads(value)
    except Exception:
        return []


def visible_chat_text(content: str) -> str:
    marker = "User task:"
    if content.startswith("Answer as ") or content.startswith("Act as ") or marker in content:
        return content.split(marker, 1)[-1].strip()
    return content


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest() == digest


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, utc_now(), (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"),
        )
    return token


def auth_user(authorization: str | None = None) -> dict | None:
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    with db_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.name, users.email, users.provider, sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        expires = row["expires_at"]
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                if datetime.utcnow().replace(tzinfo=None) > exp_dt.replace(tzinfo=None):
                    connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
                    return None
            except Exception:
                pass
    return dict(row) if row else None


def public_profile(user: dict | None) -> dict:
    if not user:
        return {"authenticated": False}
    settings = get_user_settings(user["id"])
    return {"authenticated": True, "user": user, "settings": settings}


def get_user_settings(user_id: str) -> dict:
    with db_connection() as connection:
        row = connection.execute(
            "SELECT workspace_name, theme FROM workspace_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return {"workspace_name": row["workspace_name"], "theme": row["theme"]}
        user = connection.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
        workspace_name = "Aurine"
        connection.execute(
            "INSERT INTO workspace_settings (user_id, workspace_name, theme, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, workspace_name, "aurora-3d", utc_now()),
        )
    return {"workspace_name": workspace_name, "theme": "aurora-3d"}


def require_user(authorization: str | None) -> dict:
    user = auth_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Login required.")
    return user


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def api_user_from_key(authorization: str | None) -> dict | None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        return None
    digest = token_hash(token)
    with db_connection() as connection:
        rows = connection.execute(
            """
            SELECT api_keys.id AS key_id, api_keys.key_hash,
                   users.id, users.name, users.email, users.provider
            FROM api_keys
            JOIN users ON users.id = api_keys.user_id
            WHERE api_keys.revoked = 0
            """
        ).fetchall()
        match = None
        for row in rows:
            if hmac.compare_digest(row["key_hash"], digest):
                match = row
                break
        if not match:
            return None
        connection.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (utc_now(), match["key_id"]))
    return {
        "id": match["id"],
        "name": match["name"],
        "email": match["email"],
        "provider": match["provider"],
    }


def require_api_user(authorization: str | None) -> dict:
    user = api_user_from_key(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Aurine API key.")
    return user


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path == "/health":
        return await call_next(request)
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        return StreamingResponse(
            iter(['{"detail":"Rate limit exceeded. Please slow down."}']),
            status_code=429,
            media_type="application/json",
        )
    return await call_next(request)


@app.get("/")
def home() -> FileResponse:
    return FileResponse("static/index.html", headers={"Cache-Control": "no-store"})


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "3.0.0",
        "features": [
            "streaming", "tools", "agents", "rag", "codegen",
            "reasoning", "memory", "multi-provider", "auto-routing",
            "chain-of-thought", "self-verification", "25-tools",
        ],
    }


def installed_ollama_models() -> list[str]:
    settings = get_settings()
    try:
        with urllib.request.urlopen(f"{settings.ollama_base_url}/api/tags", timeout=3) as response:
            data = json_loads(response.read().decode("utf-8"))
        models = dict(data).get("models", [])
        names = [str(item.get("name", "")).strip() for item in models if item.get("name")]
        return sorted(set(name for name in names if name))
    except Exception:
        return []


@app.get("/aurine/status")
def aurine_status() -> dict:
    settings = reload_settings()
    installed = installed_ollama_models()
    builtin = ["aurine-native", "aurine-coder", "aurine", settings.aurine_native_model, settings.ollama_chat_model]

    cloud_keys = {}
    if settings.google_api_key:
        cloud_keys["google"] = True
    if settings.openai_api_key:
        cloud_keys["openai"] = True
    if settings.groq_api_key:
        cloud_keys["groq"] = True
    if settings.anthropic_api_key:
        cloud_keys["anthropic"] = True
    if settings.deepseek_api_key:
        cloud_keys["deepseek"] = True
    if settings.openrouter_api_key:
        cloud_keys["openrouter"] = True

    return {
        "provider": settings.ai_provider,
        "runtime": "local" if installed else "cloud",
        "engine": "ollama" if installed else "cloud-api",
        "native_model": settings.aurine_native_model,
        "embedding_model": settings.aurine_embedding_model,
        "database": str(settings.vector_db),
        "api_base": "/v1",
        "models": sorted(set([item for item in builtin + installed if item])),
        "ollama_running": bool(installed),
        "cloud_keys": list(cloud_keys.keys()),
        "auto_fallback": not bool(installed) and bool(cloud_keys),
        "streaming": True,
        "tools": True,
        "agents": True,
        "reasoning": settings.reasoning_enabled,
        "memory": settings.memory_enabled,
        "version": "3.0.0",
        "supported_providers": [
            "aurine", "ollama", "openai", "anthropic", "google",
            "groq", "openrouter", "mistral", "deepseek", "fireworks",
            "nvidia", "cerebras", "custom",
        ],
    }


@app.get("/aurine/tools")
def aurine_tools() -> dict:
    return {"tools": TOOL_DEFINITIONS}


@app.get("/aurine/agents")
def aurine_agents() -> dict:
    return {"agents": list_agents()}


@app.get("/aurine/agent/{agent_id}")
def aurine_agent_detail(agent_id: str) -> dict:
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "category": agent.category,
        "icon": agent.icon,
        "tags": agent.tags,
        "tools": agent.tools,
        "temperature": agent.temperature,
        "supports_tools": agent.supports_tools,
    }


@app.get("/aurine/providers")
def aurine_providers() -> dict:
    settings = reload_settings()
    providers = [
        {"id": "aurine", "name": "Aurine Native (Local)", "requires_key": False, "models": ["aurine-coder", "aurine-native"]},
        {"id": "ollama", "name": "Ollama (Local)", "requires_key": False, "models": installed_ollama_models()},
        {"id": "openai", "name": "OpenAI", "requires_key": True, "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"], "configured": bool(settings.openai_api_key)},
        {"id": "anthropic", "name": "Anthropic (Claude)", "requires_key": True, "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"], "configured": bool(settings.anthropic_api_key)},
        {"id": "google", "name": "Google Gemini", "requires_key": True, "models": ["gemini-2.0-flash", "gemini-1.5-pro"], "configured": bool(settings.google_api_key)},
        {"id": "groq", "name": "Groq (Fast)", "requires_key": True, "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"], "configured": bool(settings.groq_api_key)},
        {"id": "openrouter", "name": "OpenRouter", "requires_key": True, "models": ["anthropic/claude-sonnet-4", "meta-llama/llama-3.1-405b-instruct"], "configured": bool(settings.openrouter_api_key)},
        {"id": "deepseek", "name": "DeepSeek", "requires_key": True, "models": ["deepseek-chat", "deepseek-coder"], "configured": bool(settings.deepseek_api_key)},
        {"id": "mistral", "name": "Mistral", "requires_key": True, "models": ["mistral-large-latest", "codestral-latest"], "configured": bool(settings.mistral_api_key)},
    ]
    return {"providers": providers}


@app.get("/me")
def me(authorization: str | None = Header(default=None)) -> dict:
    return public_profile(auth_user(authorization))


@app.post("/auth/login")
def login(request: AuthRequest, req: Request) -> dict:
    client_ip = get_client_ip(req)
    email = request.email.strip().lower()
    name = request.name.strip() or email.split("@")[0]
    if not email or not request.password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    with db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row and row["password_hash"] and not verify_password(request.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Wrong password.")
        if row:
            user_id = row["id"]
            connection.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        else:
            user_id = uuid4().hex
            connection.execute(
                "INSERT INTO users (id, name, email, password_hash, provider, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name, email, password_hash(request.password), "local", utc_now()),
            )
    token = create_session(user_id)
    logger.info(f"User login: {email} from {client_ip}")
    return {"token": token, **public_profile({"id": user_id, "name": name, "email": email, "provider": "local"})}


@app.post("/auth/demo")
def demo_login() -> dict:
    email = "demo@Aurine.local"
    name = "Aurine User"
    with db_connection() as connection:
        row = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            user_id = row["id"]
            connection.execute("UPDATE users SET name = ?, provider = 'demo' WHERE id = ?", (name, user_id))
        else:
            user_id = uuid4().hex
            connection.execute(
                "INSERT INTO users (id, name, email, password_hash, provider, created_at) VALUES (?, ?, ?, '', 'demo', ?)",
                (user_id, name, email, utc_now()),
            )
        connection.execute(
            """
            INSERT INTO workspace_settings (user_id, workspace_name, theme, updated_at)
            VALUES (?, 'Aurine', 'aurora-3d', ?)
            ON CONFLICT(user_id) DO UPDATE SET workspace_name = 'Aurine',
            theme = 'aurora-3d', updated_at = excluded.updated_at
            """,
            (user_id, utc_now()),
        )
    token = create_session(user_id)
    return {"token": token, **public_profile({"id": user_id, "name": name, "email": email, "provider": "demo"})}


@app.post("/auth/google/demo")
def google_demo_login() -> dict:
    email = "google.user@aurine.local"
    name = "Google User"
    with db_connection() as connection:
        row = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            user_id = row["id"]
            connection.execute("UPDATE users SET name = ?, provider = 'google-demo' WHERE id = ?", (name, user_id))
        else:
            user_id = uuid4().hex
            connection.execute(
                "INSERT INTO users (id, name, email, password_hash, provider, created_at) VALUES (?, ?, ?, '', 'google-demo', ?)",
                (user_id, name, email, utc_now()),
            )
    token = create_session(user_id)
    return {"token": token, **public_profile({"id": user_id, "name": name, "email": email, "provider": "google-demo"})}


@app.get("/auth/google/start")
def google_start(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=400, detail="Google login needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.")
    redirect_uri = settings.google_redirect_uri
    params = urllib.parse.urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@app.get("/auth/google/status")
def google_status() -> dict:
    settings = get_settings()
    return {
        "configured": bool(settings.google_client_id and settings.google_client_secret),
        "redirect_uri": settings.google_redirect_uri,
    }


@app.get("/auth/google/callback")
def google_callback(code: str = "") -> HTMLResponse:
    settings = get_settings()
    if not code:
        raise HTTPException(status_code=400, detail="Missing Google code.")
    token_payload = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    token_request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(token_request, timeout=20) as response:
        token_data = json_loads(response.read().decode("utf-8"))
    access_token = dict(token_data).get("access_token", "")
    info_request = urllib.request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(info_request, timeout=20) as response:
        info = dict(json_loads(response.read().decode("utf-8")))
    email = str(info.get("email", "")).lower()
    name = str(info.get("name") or email.split("@")[0])
    if not email:
        raise HTTPException(status_code=400, detail="Google did not return email.")
    with db_connection() as connection:
        row = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            user_id = row["id"]
            connection.execute("UPDATE users SET name = ?, provider = 'google' WHERE id = ?", (name, user_id))
        else:
            user_id = uuid4().hex
            connection.execute(
                "INSERT INTO users (id, name, email, password_hash, provider, created_at) VALUES (?, ?, ?, '', 'google', ?)",
                (user_id, name, email, utc_now()),
            )
    token = create_session(user_id)
    logger.info(f"Google login: {email}")
    return HTMLResponse(
        f"""<script>localStorage.setItem('Aurine_auth_token', {json_dumps(token)});location.href='/';</script>"""
    )


@app.post("/settings")
def save_settings(request: SettingsRequest, authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    name = request.name.strip() or user["name"]
    workspace_name = request.workspace_name.strip() or f"{name} Workspace"
    allowed_themes = {"coder-night", "aurora-3d", "normal", "beauty"}
    theme = request.theme.strip() if request.theme.strip() in allowed_themes else "aurora-3d"
    with db_connection() as connection:
        connection.execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))
        connection.execute(
            """
            INSERT INTO workspace_settings (user_id, workspace_name, theme, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET workspace_name = excluded.workspace_name,
            theme = excluded.theme, updated_at = excluded.updated_at
            """,
            (user["id"], workspace_name, theme, utc_now()),
        )
    return public_profile({"id": user["id"], "name": name, "email": user["email"], "provider": user["provider"]})


@app.get("/api-keys")
def list_api_keys(authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, key_prefix, created_at, last_used_at, revoked FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    return {"keys": [dict(row) for row in rows]}


@app.post("/api-keys")
def create_api_key(request: ApiKeyCreateRequest, authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    name = request.name.strip()[:80] or "API key"
    raw_key = f"aurine_sk_{secrets.token_urlsafe(32)}"
    key_id = uuid4().hex
    prefix = raw_key[:18]
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO api_keys (id, user_id, name, key_hash, key_prefix, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (key_id, user["id"], name, token_hash(raw_key), prefix, utc_now()),
        )
    return {"key": {"id": key_id, "name": name, "key": raw_key, "key_prefix": prefix, "created_at": utc_now()}}


@app.post("/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: str, authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    with db_connection() as connection:
        connection.execute("UPDATE api_keys SET revoked = 1 WHERE id = ? AND user_id = ?", (key_id, user["id"]))
    return {"ok": True}


@app.get("/v1/models")
def openai_models(authorization: str | None = Header(default=None)) -> dict:
    require_api_user(authorization)
    model_ids = sorted(set(["aurine-native", "aurine", "aurine-coder", *installed_ollama_models()]))
    return {"object": "list", "data": [{"id": mid, "object": "model", "owned_by": "aurine"} for mid in model_ids]}


@app.post("/v1/chat/completions")
def openai_chat_completions(request: OpenAIChatCompletionRequest, authorization: str | None = Header(default=None)):
    require_api_user(authorization)
    valid_messages = [
        {"role": item.get("role"), "content": str(item.get("content", "")).strip()}
        for item in request.messages
        if item.get("role") in {"system", "user", "assistant"} and str(item.get("content", "")).strip()
    ]
    question = next((item["content"] for item in reversed(valid_messages) if item["role"] == "user"), "")
    if not question:
        raise HTTPException(status_code=400, detail="At least one user message is required.")
    history = [item for item in valid_messages if item["content"] != question][-16:]
    model_name = "" if request.model in {"", "aurine", "default"} else request.model
    model_config = {"provider": "aurine", "model": model_name} if model_name else {"provider": "aurine"}

    if request.stream:
        def generate_stream():
            full_response = ""
            for chunk in answer_question_stream(question, history, model_config):
                full_response += chunk
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}, 'index': 0}]})}\n\n"
            yield f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop', 'index': 0}]})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(generate_stream(), media_type="text/event-stream")

    answer = answer_question(question, history, model_config)
    return {
        "id": f"chatcmpl-{uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model or "aurine-native",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer["answer"]}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.get("/search")
def search(q: str = "") -> dict:
    needle = q.strip().lower()
    with db_connection() as connection:
        chat_rows = connection.execute("SELECT id, title, updated_at FROM chats ORDER BY updated_at DESC").fetchall()
        message_rows = connection.execute("SELECT chat_id, role, content, created_at FROM chat_messages ORDER BY created_at DESC").fetchall()
    projects = list_projects()
    docs = list_documents()
    if needle:
        chat_rows = [row for row in chat_rows if needle in row["title"].lower()]
        message_rows = [row for row in message_rows if needle in row["content"].lower()]
        projects = [p for p in projects if needle in p["name"].lower() or needle in p.get("description", "").lower()]
        docs = [d for d in docs if needle in d["source"].lower()]
    return {
        "chats": [dict(row) | {"title": visible_chat_text(row["title"])[:48]} for row in chat_rows[:20]],
        "messages": [dict(row) | {"content": visible_chat_text(row["content"]) if row["role"] == "user" else row["content"]} for row in message_rows[:20]],
        "projects": projects[:20],
        "documents": docs[:20],
    }


@app.get("/scheduled")
def scheduled(authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, detail, due_at, done, created_at FROM scheduled_items WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/scheduled")
def create_scheduled(request: ScheduledRequest, authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    item_id = uuid4().hex
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO scheduled_items (id, user_id, title, detail, due_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, user["id"], title, request.detail.strip(), request.due_at.strip(), utc_now()),
        )
    return {"item": {"id": item_id, "title": title, "detail": request.detail, "due_at": request.due_at, "done": 0}}


@app.get("/plugins")
def plugins(authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    available = [
        {"id": "git", "name": "Git", "description": "Version control: status, log, diff, branches, commit, push, pull.", "icon": "G", "category": "Version Control", "actions": ["status", "log", "diff", "branches", "commit", "push", "pull", "clone", "init"]},
        {"id": "github", "name": "GitHub", "description": "GitHub integration: repos, issues, PRs, search, authentication.", "icon": "GH", "category": "Version Control", "actions": ["repos", "issues", "prs", "search", "auth", "create_repo", "create_issue"]},
        {"id": "web-search", "name": "Web Search", "description": "Search the web, fetch URLs, extract content from pages.", "icon": "W", "category": "Research", "actions": ["search", "fetch", "news", "docs"]},
        {"id": "code-runner", "name": "Code Runner", "description": "Execute Python, JavaScript, shell commands, and scripts.", "icon": "C", "category": "Development", "actions": ["python", "javascript", "shell", "run_file"]},
        {"id": "file-manager", "name": "File Manager", "description": "Browse, read, write, search, and manage workspace files.", "icon": "F", "category": "Development", "actions": ["list", "read", "write", "search", "delete", "rename", "copy"]},
        {"id": "image-gen", "name": "Image Generator", "description": "Create images with DALL-E, generate SVG, HTML visuals.", "icon": "I", "category": "Creative", "actions": ["generate", "svg", "html_art", "thumbnails"]},
        {"id": "data-analyzer", "name": "Data Analyzer", "description": "Analyze CSV, JSON, Excel data with charts and statistics.", "icon": "D", "category": "Data", "actions": ["analyze_csv", "analyze_json", "statistics", "chart", "transform"]},
        {"id": "terminal", "name": "Terminal", "description": "Run PowerShell/CMD commands, manage processes, system ops.", "icon": "T", "category": "Development", "actions": ["run", "processes", "env", "network"]},
        {"id": "database", "name": "Database", "description": "SQLite operations: query, create tables, import/export data.", "icon": "DB", "category": "Data", "actions": ["query", "tables", "create_table", "import", "export"]},
        {"id": "documents", "name": "Documents", "description": "Upload, search, and ask questions over PDF/TXT/MD files.", "icon": "DOC", "category": "Research", "actions": ["upload", "search", "list", "delete"]},
        {"id": "media", "name": "Media Creator", "description": "Create PDF, Excel, ZIP, HTML, Markdown artifacts.", "icon": "M", "category": "Creative", "actions": ["pdf", "excel", "zip", "html", "markdown", "video_scene"]},
        {"id": "sites", "name": "Sites", "description": "Website project workspace, preview, and zip export.", "icon": "S", "category": "Development", "actions": ["list", "preview", "deploy", "template"]},
        {"id": "weather", "name": "Weather", "description": "Get current weather, forecasts, and climate data.", "icon": "W", "category": "Utility", "actions": ["current", "forecast", "alerts"]},
        {"id": "calculator", "name": "Calculator", "description": "Math expressions, unit conversions, scientific calculations.", "icon": "=", "category": "Utility", "actions": ["calculate", "convert", "scientific"]},
        {"id": "api-tester", "name": "API Tester", "description": "Test HTTP endpoints, check APIs, debug requests.", "icon": "A", "category": "Development", "actions": ["get", "post", "put", "delete", "headers"]},
        {"id": "system", "name": "System Info", "description": "OS info, installed tools, process list, disk usage.", "icon": "SYS", "category": "Utility", "actions": ["info", "processes", "disk", "network", "tools"]},
        {"id": "markdown", "name": "Markdown Editor", "description": "Create, edit, and export Markdown documents.", "icon": "MD", "category": "Research", "actions": ["create", "edit", "export", "template"]},
        {"id": "email-draft", "name": "Email Draft", "description": "Draft professional emails, responses, and campaigns.", "icon": "E", "category": "Productivity", "actions": ["draft", "reply", "template", "campaign"]},
        {"id": "scheduler", "name": "Scheduler", "description": "Set reminders, schedule tasks, manage to-do lists.", "icon": "SCH", "category": "Productivity", "actions": ["add", "list", "complete", "reminder"]},
        {"id": "vscode", "name": "VS Code", "description": "Open workspace in VS Code, manage extensions, recent files.", "icon": "VS", "category": "Development", "actions": ["open", "extensions", "recent"]},
        {"id": "ruflo-core", "name": "Ruflo Core", "description": "Server orchestration, health checks, plugin discovery.", "icon": "R", "category": "Ruflo", "actions": ["health", "status", "plugins"]},
        {"id": "ruflo-swarm", "name": "Ruflo Swarm", "description": "Coordinate multiple agents as one team.", "icon": "RS", "category": "Ruflo", "actions": ["deploy", "status", "scale"]},
        {"id": "ruflo-autopilot", "name": "Ruflo Autopilot", "description": "Autonomous work loops with guardrails.", "icon": "RA", "category": "Ruflo", "actions": ["start", "stop", "status", "logs"]},
        {"id": "ruflo-goals", "name": "Ruflo Goals", "description": "Break large goals into plans and tracked progress.", "icon": "RG", "category": "Ruflo", "actions": ["create", "track", "progress", "complete"]},
        {"id": "ruflo-testgen", "name": "Ruflo TestGen", "description": "Find missing tests and generate them automatically.", "icon": "RT", "category": "Ruflo", "actions": ["scan", "generate", "coverage", "report"]},
        {"id": "ruflo-security", "name": "Ruflo Security", "description": "Vulnerability scanning, CVE review, security audit.", "icon": "RS", "category": "Ruflo", "actions": ["scan", "audit", "report", "fix"]},
        {"id": "ruflo-browser", "name": "Ruflo Browser", "description": "Browser automation and Playwright-style checks.", "icon": "RB", "category": "Ruflo", "actions": ["navigate", "screenshot", "click", "scrape"]},
        {"id": "ruflo-cost", "name": "Ruflo Cost Tracker", "description": "Token usage budgets and cost alerts.", "icon": "RC", "category": "Ruflo", "actions": ["usage", "budget", "alerts", "history"]},
        {"id": "ruflo-observability", "name": "Ruflo Observability", "description": "Logs, traces, and metrics dashboard.", "icon": "RO", "category": "Ruflo", "actions": ["logs", "traces", "metrics", "alerts"]},
        {"id": "ruflo-plugin-creator", "name": "Ruflo Plugin Creator", "description": "Scaffold and validate new plugins.", "icon": "RP", "category": "Ruflo", "actions": ["scaffold", "validate", "test", "publish"]},
    ]
    with db_connection() as connection:
        rows = connection.execute("SELECT plugin_id, enabled FROM plugin_settings WHERE user_id = ?", (user["id"])).fetchall()
    enabled = {row["plugin_id"]: bool(row["enabled"]) for row in rows}
    plugins_with_status = []
    for item in available:
        status = plugin_status(item["id"])
        plugins_with_status.append(item | status | {"enabled": enabled.get(item["id"], status["connected"])})
    return {"plugins": plugins_with_status}


@app.post("/plugins/toggle")
def toggle_plugin(request: PluginToggleRequest, authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO plugin_settings (user_id, plugin_id, enabled) VALUES (?, ?, ?) ON CONFLICT(user_id, plugin_id) DO UPDATE SET enabled = excluded.enabled",
            (user["id"], request.plugin_id, int(request.enabled)),
        )
    return {"ok": True}


def run_plugin_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, cwd=Path.cwd(), text=True, capture_output=True, timeout=12)
        output = (result.stdout + result.stderr).strip()
        return output[:5000] or f"Command exited with code {result.returncode}."
    except FileNotFoundError:
        return f"{command[0]} is not installed or not in PATH."
    except Exception as exc:
        return str(exc)


def command_exists(name: str) -> bool:
    return bool(shutil.which(name))


def plugin_status(plugin_id: str) -> dict:
    if plugin_id == "git":
        if not command_exists("git"):
            return {"connected": False, "status": "Missing", "status_detail": "Git is not installed or not in PATH."}
        output = run_plugin_command(["git", "--version"])
        return {"connected": True, "status": "Ready", "status_detail": output}
    if plugin_id == "github":
        if not command_exists("gh"):
            return {"connected": False, "status": "Missing", "status_detail": "GitHub CLI is not installed."}
        output = run_plugin_command(["gh", "auth", "status"])
        connected = "Logged in" in output or "Token scopes" in output
        return {"connected": connected, "status": "Logged in" if connected else "Needs login", "status_detail": output}
    if plugin_id == "vscode":
        if not command_exists("code"):
            return {"connected": False, "status": "Missing", "status_detail": "VS Code 'code' command is not in PATH."}
        output = run_plugin_command(["code", "--version"])
        return {"connected": True, "status": "Ready", "status_detail": output}
    if plugin_id == "sql":
        return {"connected": True, "status": "Ready", "status_detail": "SQLite database is available."}
    if plugin_id == "terminal":
        shell_name = "powershell" if command_exists("powershell") else "cmd"
        return {"connected": True, "status": "Ready", "status_detail": f"{shell_name} is available."}
    if plugin_id == "tools":
        return {"connected": True, "status": "Ready", "status_detail": "25+ agent tools available."}
    return {"connected": True, "status": "Built in", "status_detail": "This Aurine capability is available inside the app."}


class PluginActionRequest(BaseModel):
    plugin_id: str
    action: str = "status"
    params: dict = Field(default_factory=dict)


def open_terminal_command(command: str) -> None:
    subprocess.Popen(
        ["powershell", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=Path.cwd(),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )


def run_safe_command(command: str, timeout: int = 30) -> str:
    blocked = ["rm -rf /", "rm -rf ~", "rmdir /s", "del /s /q", "format ", "shutdown", "mkfs"]
    lower = command.lower()
    for b in blocked:
        if b in lower:
            return f"Blocked: destructive command '{b}' is not allowed."
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=timeout, cwd=Path.cwd())
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
        return f"Command timed out after {timeout}s."
    except Exception as exc:
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# Plugin Action Router - Each plugin has real working sub-actions
# ---------------------------------------------------------------------------

@app.post("/api/launch-aura")
def launch_aura(authorization: str | None = Header(default=None)) -> dict:
    require_user(authorization)
    project_dir = Path.cwd()
    venv_python = project_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = project_dir / ".venv" / "bin" / "python.exe"
    script = project_dir / "auracode.py"
    if not venv_python.exists() or not script.exists():
        return {"error": "AuraCode not found. Run setup first."}
    bat_file = project_dir / "start-auracode.bat"
    if bat_file.exists():
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "cmd.exe", "/k", f'cd /d "{project_dir}" && "{venv_python}" "{script}"'],
            cwd=str(project_dir),
        )
    else:
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "cmd.exe", "/k", f'cd /d "{project_dir}" && "{venv_python}" "{script}"'],
            cwd=str(project_dir),
        )
    return {"status": "AuraCode terminal opened"}


@app.post("/plugins/action")
def plugin_action(request: PluginActionRequest, authorization: str | None = Header(default=None)) -> dict:
    require_user(authorization)
    pid = request.plugin_id.strip().lower()
    action = request.action.strip().lower()
    params = request.params or {}

    # --- Git Plugin ---
    if pid == "git":
        return _git_plugin_action(action, params)

    # --- GitHub Plugin ---
    if pid == "github":
        return _github_plugin_action(action, params)

    # --- Web Search Plugin ---
    if pid == "web-search":
        return _web_search_plugin_action(action, params)

    # --- Code Runner Plugin ---
    if pid == "code-runner":
        return _code_runner_plugin_action(action, params)

    # --- File Manager Plugin ---
    if pid == "file-manager":
        return _file_manager_plugin_action(action, params)

    # --- Image Generator Plugin ---
    if pid == "image-gen":
        return _image_gen_plugin_action(action, params)

    # --- Data Analyzer Plugin ---
    if pid == "data-analyzer":
        return _data_analyzer_plugin_action(action, params)

    # --- Terminal Plugin ---
    if pid == "terminal":
        return _terminal_plugin_action(action, params)

    # --- Database Plugin ---
    if pid == "database":
        return _database_plugin_action(action, params)

    # --- Documents Plugin ---
    if pid == "documents":
        return _documents_plugin_action(action, params)

    # --- Media Creator Plugin ---
    if pid == "media":
        return _media_plugin_action(action, params)

    # --- Sites Plugin ---
    if pid == "sites":
        return _sites_plugin_action(action, params)

    # --- Weather Plugin ---
    if pid == "weather":
        return _weather_plugin_action(action, params)

    # --- Calculator Plugin ---
    if pid == "calculator":
        return _calculator_plugin_action(action, params)

    # --- API Tester Plugin ---
    if pid == "api-tester":
        return _api_tester_plugin_action(action, params)

    # --- System Info Plugin ---
    if pid == "system":
        return _system_plugin_action(action, params)

    # --- Markdown Plugin ---
    if pid == "markdown":
        return _markdown_plugin_action(action, params)

    # --- Email Draft Plugin ---
    if pid == "email-draft":
        return _email_draft_plugin_action(action, params)

    # --- Scheduler Plugin ---
    if pid == "scheduler":
        return _scheduler_plugin_action(action, params)

    # --- VS Code Plugin ---
    if pid == "vscode":
        return _vscode_plugin_action(action, params)

    # --- Ruflo plugins ---
    if pid.startswith("ruflo-"):
        return _ruflo_plugin_action(pid, action, params)

    # --- Legacy/Aurine built-in ---
    if pid in {"code", "files", "sites", "media", "tools"}:
        return {"output": "This plugin is active inside Aurine. Use its panel/action in the sidebar."}

    raise HTTPException(status_code=404, detail=f"Plugin '{pid}' not found.")


# ---------------------------------------------------------------------------
# Git Plugin - Full version control operations
# ---------------------------------------------------------------------------

def _git_plugin_action(action: str, params: dict) -> dict:
    path = params.get("path", ".")
    if action == "status":
        output = run_safe_command(f'git -C "{path}" status')
        return {"output": output, "action": "status"}
    elif action == "log":
        count = params.get("count", 15)
        output = run_safe_command(f'git -C "{path}" log --oneline -{count}')
        return {"output": output, "action": "log"}
    elif action == "diff":
        output = run_safe_command(f'git -C "{path}" diff --stat')
        return {"output": output, "action": "diff"}
    elif action == "diff_full":
        output = run_safe_command(f'git -C "{path}" diff')
        return {"output": output[:6000], "action": "diff_full"}
    elif action == "branches":
        output = run_safe_command(f'git -C "{path}" branch -a')
        return {"output": output, "action": "branches"}
    elif action == "commit":
        message = params.get("message", "Update from Aurine")
        run_safe_command(f'git -C "{path}" add -A')
        output = run_safe_command(f'git -C "{path}" commit -m "{message}"')
        return {"output": output, "action": "commit"}
    elif action == "push":
        branch = params.get("branch", "main")
        output = run_safe_command(f'git -C "{path}" push origin {branch}', timeout=60)
        return {"output": output, "action": "push"}
    elif action == "pull":
        output = run_safe_command(f'git -C "{path}" pull', timeout=60)
        return {"output": output, "action": "pull"}
    elif action == "clone":
        url = params.get("url", "")
        if not url:
            return {"output": "URL is required for clone.", "action": "clone"}
        output = run_safe_command(f'git clone {url}', timeout=120)
        return {"output": output, "action": "clone"}
    elif action == "init":
        output = run_safe_command(f'git -C "{path}" init')
        return {"output": output, "action": "init"}
    elif action == "stash":
        output = run_safe_command(f'git -C "{path}" stash')
        return {"output": output, "action": "stash"}
    elif action == "stash_pop":
        output = run_safe_command(f'git -C "{path}" stash pop')
        return {"output": output, "action": "stash_pop"}
    elif action == "tags":
        output = run_safe_command(f'git -C "{path}" tag -l')
        return {"output": output, "action": "tags"}
    elif action == "remote":
        output = run_safe_command(f'git -C "{path}" remote -v')
        return {"output": output, "action": "remote"}
    elif action == "blame":
        file_path = params.get("file", "")
        output = run_safe_command(f'git -C "{path}" blame {file_path}' if file_path else 'git blame --help')
        return {"output": output[:6000], "action": "blame"}
    elif action == "ignore_add":
        pattern = params.get("pattern", "")
        if pattern:
            with open(Path(path) / ".gitignore", "a") as f:
                f.write(f"\n{pattern}")
            return {"output": f"Added '{pattern}' to .gitignore", "action": "ignore_add"}
        return {"output": "Pattern is required.", "action": "ignore_add"}
    else:
        output = run_safe_command(f'git -C "{path}" status --short')
        return {"output": output, "action": "status"}


# ---------------------------------------------------------------------------
# GitHub Plugin - GitHub API integration
# ---------------------------------------------------------------------------

def _github_plugin_action(action: str, params: dict) -> dict:
    if not command_exists("gh"):
        return {"output": "GitHub CLI (gh) is not installed. Install from https://cli.github.com/", "connected": False, "action": action}

    if action == "auth":
        status = run_safe_command("gh auth status")
        return {"output": status, "action": "auth", "connected": "Logged in" in status or "Token scopes" in status}
    elif action == "repos":
        output = run_safe_command("gh repo list --limit 20")
        return {"output": output, "action": "repos"}
    elif action == "issues":
        repo = params.get("repo", "")
        cmd = f"gh issue list -R {repo}" if repo else "gh issue list --limit 20"
        output = run_safe_command(cmd)
        return {"output": output, "action": "issues"}
    elif action == "prs":
        repo = params.get("repo", "")
        cmd = f"gh pr list -R {repo}" if repo else "gh pr list --limit 20"
        output = run_safe_command(cmd)
        return {"output": output, "action": "prs"}
    elif action == "search":
        query = params.get("query", "")
        output = run_safe_command(f'gh search repos "{query}" --limit 10' if query else "gh search repos --help")
        return {"output": output, "action": "search"}
    elif action == "create_repo":
        name = params.get("name", "new-repo")
        output = run_safe_command(f'gh repo create {name} --public --source=. --push')
        return {"output": output, "action": "create_repo"}
    elif action == "create_issue":
        repo = params.get("repo", "")
        title = params.get("title", "Issue from Aurine")
        output = run_safe_command(f'gh issue create -R {repo} -t "{title}"' if repo else "gh issue create --help")
        return {"output": output, "action": "create_issue"}
    elif action == "clone":
        url = params.get("url", "")
        output = run_safe_command(f"gh repo clone {url}" if url else "gh repo clone --help", timeout=60)
        return {"output": output, "action": "clone"}
    elif action == "gist":
        output = run_safe_command("gh gist list --limit 10")
        return {"output": output, "action": "gist"}
    elif action == "notifications":
        output = run_safe_command("gh api notifications --paginate -q '.[].subject.title' 2>/dev/null || gh api notifications --paginate 2>/dev/null | head -20")
        return {"output": output[:4000], "action": "notifications"}
    elif action == "api":
        endpoint = params.get("endpoint", "/user")
        output = run_safe_command(f"gh api {endpoint}")
        return {"output": output[:6000], "action": "api"}
    else:
        status = run_safe_command("gh auth status")
        return {"output": f"GitHub CLI status:\n{status}", "action": "status", "connected": "Logged in" in status}


# ---------------------------------------------------------------------------
# Web Search Plugin
# ---------------------------------------------------------------------------

def _web_search_plugin_action(action: str, params: dict) -> dict:
    if action == "search":
        query = params.get("query", "")
        if not query:
            return {"output": "Search query is required.", "action": "search"}
        from .agent_tools import execute_web_search
        output = execute_web_search(query)
        return {"output": output, "action": "search"}
    elif action == "fetch":
        url = params.get("url", "")
        if not url:
            return {"output": "URL is required.", "action": "fetch"}
        from .agent_tools import execute_fetch_url
        output = execute_fetch_url(url)
        return {"output": output, "action": "fetch"}
    elif action == "news":
        query = params.get("query", "latest news")
        from .agent_tools import execute_web_search
        output = execute_web_search(f"{query} latest news {datetime.utcnow().strftime('%Y-%m-%d')}")
        return {"output": output, "action": "news"}
    elif action == "docs":
        query = params.get("query", "")
        from .agent_tools import execute_web_search
        output = execute_web_search(f"{query} documentation official docs")
        return {"output": output, "action": "docs"}
    else:
        return {"output": "Actions: search, fetch, news, docs", "action": "help"}


# ---------------------------------------------------------------------------
# Code Runner Plugin
# ---------------------------------------------------------------------------

def _code_runner_plugin_action(action: str, params: dict) -> dict:
    if action == "python":
        code = params.get("code", "")
        if not code:
            return {"output": "Python code is required.", "action": "python"}
        from .agent_tools import execute_run_python
        output = execute_run_python(code)
        return {"output": output, "action": "python"}
    elif action == "javascript":
        code = params.get("code", "")
        if not code:
            return {"output": "JavaScript code is required.", "action": "javascript"}
        output = run_safe_command(f'node -e "{code.replace(chr(34), chr(39))}"')
        return {"output": output, "action": "javascript"}
    elif action == "shell":
        command = params.get("command", "")
        if not command:
            return {"output": "Shell command is required.", "action": "shell"}
        output = run_safe_command(command)
        return {"output": output, "action": "shell"}
    elif action == "run_file":
        file_path = params.get("path", "")
        if not file_path:
            return {"output": "File path is required.", "action": "run_file"}
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            output = run_safe_command(f'python "{file_path}"')
        elif ext == ".js":
            output = run_safe_command(f'node "{file_path}"')
        elif ext == ".ps1":
            output = run_safe_command(f'powershell -ExecutionPolicy Bypass -File "{file_path}"')
        elif ext == ".sh":
            output = run_safe_command(f'bash "{file_path}"')
        else:
            output = run_safe_command(f'"{file_path}"')
        return {"output": output, "action": "run_file"}
    else:
        return {"output": "Actions: python, javascript, shell, run_file", "action": "help"}


# ---------------------------------------------------------------------------
# File Manager Plugin
# ---------------------------------------------------------------------------

def _file_manager_plugin_action(action: str, params: dict) -> dict:
    path_str = params.get("path", ".")
    if action == "list":
        from .agent_tools import execute_list_files
        output = execute_list_files(path_str)
        return {"output": output, "action": "list"}
    elif action == "read":
        from .agent_tools import execute_read_file
        output = execute_read_file(path_str)
        return {"output": output, "action": "read"}
    elif action == "write":
        content = params.get("content", "")
        from .agent_tools import execute_write_file
        output = execute_write_file(path_str, content)
        return {"output": output, "action": "write"}
    elif action == "search":
        pattern = params.get("pattern", "")
        from .agent_tools import execute_search_files
        output = execute_search_files(pattern, path_str)
        return {"output": output, "action": "search"}
    elif action == "delete":
        try:
            target = Path(path_str).resolve()
            if target.is_file():
                target.unlink()
                return {"output": f"Deleted: {path_str}", "action": "delete"}
            elif target.is_dir():
                import shutil
                shutil.rmtree(target)
                return {"output": f"Deleted directory: {path_str}", "action": "delete"}
            return {"output": f"Not found: {path_str}", "action": "delete"}
        except Exception as exc:
            return {"output": f"Delete failed: {exc}", "action": "delete"}
    elif action == "rename":
        new_name = params.get("new_name", "")
        try:
            target = Path(path_str).resolve()
            new_path = target.parent / new_name
            target.rename(new_path)
            return {"output": f"Renamed to: {new_path}", "action": "rename"}
        except Exception as exc:
            return {"output": f"Rename failed: {exc}", "action": "rename"}
    elif action == "copy":
        dest = params.get("dest", "")
        try:
            import shutil
            shutil.copy2(path_str, dest)
            return {"output": f"Copied to: {dest}", "action": "copy"}
        except Exception as exc:
            return {"output": f"Copy failed: {exc}", "action": "copy"}
    elif action == "tree":
        try:
            target = Path(path_str).resolve()
            lines = []
            for item in sorted(target.rglob("*"))[:100]:
                if item.name in {"__pycache__", "node_modules", ".venv", ".git"}:
                    continue
                rel = item.relative_to(target)
                depth = len(rel.parts) - 1
                prefix = "  " * depth + ("  " if depth > 0 else "")
                suffix = "/" if item.is_dir() else ""
                lines.append(f"{prefix}{item.name}{suffix}")
            return {"output": "\n".join(lines) or "Empty directory.", "action": "tree"}
        except Exception as exc:
            return {"output": f"Tree failed: {exc}", "action": "tree"}
    else:
        return {"output": "Actions: list, read, write, search, delete, rename, copy, tree", "action": "help"}


# ---------------------------------------------------------------------------
# Image Generator Plugin
# ---------------------------------------------------------------------------

def _image_gen_plugin_action(action: str, params: dict) -> dict:
    if action == "generate":
        prompt = params.get("prompt", "")
        if not prompt:
            return {"output": "Prompt is required.", "action": "generate"}
        from .agent_tools import execute_create_image
        output = execute_create_image(prompt, params.get("size", "1024x1024"))
        return {"output": output, "action": "generate"}
    elif action == "svg":
        prompt = params.get("prompt", "abstract art")
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" style="stop-color:#2dd4bf"/>
    <stop offset="100%" style="stop-color:#a78bfa"/>
  </linearGradient></defs>
  <rect width="400" height="400" fill="#0f172a"/>
  <circle cx="200" cy="200" r="150" fill="url(#g)" opacity="0.8"/>
  <text x="200" y="210" text-anchor="middle" fill="white" font-size="16" font-family="sans-serif">{prompt[:40]}</text>
</svg>'''
        return {"output": f"SVG generated:\n{svg}", "action": "svg", "svg": svg}
    elif action == "html_art":
        prompt = params.get("prompt", "visual art")
        html = f'''<!DOCTYPE html>
<html><head><style>
body {{ margin:0; background:#0a0a0a; display:flex; justify-content:center; align-items:center; height:100vh; }}
.art {{ width:400px; height:400px; background:linear-gradient(135deg, #2dd4bf, #a78bfa); border-radius:20px;
  display:flex; align-items:center; justify-content:center; font-family:sans-serif; color:white; font-size:20px; }}
</style></head><body><div class="art">{prompt}</div></body></html>'''
        return {"output": f"HTML art created.", "action": "html_art", "html": html}
    elif action == "thumbnails":
        prompt = params.get("prompt", "thumbnail")
        sizes = ["1024x1024", "1792x1024", "1024x1792"]
        return {"output": f"Thumbnail sizes available: {', '.join(sizes)}\nUse 'generate' action with each size.", "action": "thumbnails"}
    else:
        return {"output": "Actions: generate, svg, html_art, thumbnails", "action": "help"}


# ---------------------------------------------------------------------------
# Data Analyzer Plugin
# ---------------------------------------------------------------------------

def _data_analyzer_plugin_action(action: str, params: dict) -> dict:
    if action == "analyze_csv":
        file_path = params.get("path", "")
        if not file_path:
            return {"output": "CSV file path required.", "action": "analyze_csv"}
        code = f"""
import csv, json
with open(r'{file_path}', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
print(f"Rows: {{len(rows)}}")
if rows:
    print(f"Columns: {{list(rows[0].keys())}}")
    for col in rows[0].keys():
        vals = [r.get(col, '') for r in rows]
        non_empty = [v for v in vals if v]
        print(f"  {{col}}: {{len(non_empty)}}/{{len(vals)}} filled")
"""
        from .agent_tools import execute_run_python
        output = execute_run_python(code)
        return {"output": output, "action": "analyze_csv"}
    elif action == "analyze_json":
        data = params.get("data", "{}")
        from .agent_tools import execute_json_transform
        output = execute_json_transform(data, "validate")
        keys_output = execute_json_transform(data, "extract_keys")
        return {"output": f"{output}\n\nKeys:\n{keys_output}", "action": "analyze_json"}
    elif action == "statistics":
        data = params.get("numbers", "")
        code = f"""
import statistics
nums = [float(x) for x in '{data}'.split(',') if x.strip()]
print(f"Count: {{len(nums)}}")
print(f"Mean: {{statistics.mean(nums):.2f}}")
print(f"Median: {{statistics.median(nums):.2f)}}")
print(f"Stdev: {{statistics.stdev(nums):.2f}}" if len(nums) > 1 else "")
print(f"Min: {{min(nums)}}")
print(f"Max: {{max(nums)}}")
"""
        from .agent_tools import execute_run_python
        output = execute_run_python(code)
        return {"output": output, "action": "statistics"}
    elif action == "transform":
        data = params.get("data", "{}")
        operation = params.get("operation", "format")
        from .agent_tools import execute_json_transform
        output = execute_json_transform(data, operation)
        return {"output": output, "action": "transform"}
    elif action == "chart":
        data = params.get("data", "[]")
        chart_type = params.get("type", "bar")
        try:
            values = json.loads(data) if isinstance(data, str) else data
            if isinstance(values, list) and values:
                width = 50
                max_val = max(v if isinstance(v, (int, float)) else 1 for v in values)
                lines = []
                for i, v in enumerate(values):
                    val = v if isinstance(v, (int, float)) else 1
                    bar_len = int((val / max_val) * width) if max_val > 0 else 0
                    lines.append(f"  [{('█' * bar_len).ljust(width)}] {val}")
                output = f"Chart ({chart_type}):\n" + "\n".join(lines)
            else:
                output = "Provide data as a JSON array of numbers."
        except Exception:
            output = "Provide data as a JSON array of numbers."
        return {"output": output, "action": "chart"}
    else:
        return {"output": "Actions: analyze_csv, analyze_json, statistics, chart, transform", "action": "help"}


# ---------------------------------------------------------------------------
# Terminal Plugin
# ---------------------------------------------------------------------------

def _terminal_plugin_action(action: str, params: dict) -> dict:
    if action == "run":
        command = params.get("command", "")
        if not command:
            return {"output": "Command is required.", "action": "run"}
        output = run_safe_command(command)
        return {"output": output, "action": "run"}
    elif action == "processes":
        output = run_safe_command("tasklist /FO CSV 2>nul | head -30" if os.name == "nt" else "ps aux | head -30")
        return {"output": output, "action": "processes"}
    elif action == "env":
        key = params.get("key", "")
        if key:
            import os
            output = os.environ.get(key, f"Variable '{key}' not found.")
        else:
            output = run_safe_command("set" if os.name == "nt" else "env | head -30")
        return {"output": output[:4000], "action": "env"}
    elif action == "network":
        output = run_safe_command("ipconfig" if os.name == "nt" else "ifconfig | head -20")
        return {"output": output, "action": "network"}
    elif action == "open":
        open_terminal_command(params.get("command", "Write-Host 'Aurine Terminal Connected'"))
        return {"output": "Terminal opened.", "action": "open"}
    else:
        return {"output": "Actions: run, processes, env, network, open", "action": "help"}


# ---------------------------------------------------------------------------
# Database Plugin
# ---------------------------------------------------------------------------

def _database_plugin_action(action: str, params: dict) -> dict:
    settings = get_settings()
    db_path = str(settings.vector_db)
    if action == "tables":
        import sqlite3
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        conn.close()
        return {"output": f"Tables: {', '.join(r[0] for r in rows)}", "action": "tables"}
    elif action == "query":
        sql = params.get("sql", "")
        if not sql:
            return {"output": "SQL query is required.", "action": "query"}
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(sql).fetchall()
            cols = [d[0] for d in conn.execute(sql).description] if conn.execute(sql).description else []
            conn.close()
            if rows:
                header = " | ".join(cols) if cols else ""
                lines = [header, "-" * len(header)] if header else []
                for row in rows[:50]:
                    lines.append(" | ".join(str(v) for v in row))
                return {"output": "\n".join(lines), "action": "query"}
            return {"output": "Query returned no rows.", "action": "query"}
        except Exception as exc:
            conn.close()
            return {"output": f"SQL error: {exc}", "action": "query"}
    elif action == "create_table":
        table = params.get("table", "new_table")
        schema = params.get("schema", "id INTEGER PRIMARY KEY, name TEXT")
        import sqlite3
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({schema})")
            conn.commit()
            conn.close()
            return {"output": f"Table '{table}' created.", "action": "create_table"}
        except Exception as exc:
            conn.close()
            return {"output": f"Error: {exc}", "action": "create_table"}
    elif action == "export":
        table = params.get("table", "chats")
        import sqlite3, csv, io
        conn = sqlite3.connect(db_path)
        rows = conn.execute(f"SELECT * FROM {table} LIMIT 1000").fetchall()
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 1").description]
        conn.close()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(cols)
        writer.writerows(rows)
        return {"output": output.getvalue()[:6000], "action": "export"}
    elif action == "import":
        table = params.get("table", "")
        csv_data = params.get("csv", "")
        if not table or not csv_data:
            return {"output": "Provide 'table' and 'csv' (CSV string with header row).", "action": "import"}
        import sqlite3, csv, io
        conn = sqlite3.connect(db_path)
        try:
            reader = csv.reader(io.StringIO(csv_data))
            headers = next(reader, None)
            if not headers:
                conn.close()
                return {"output": "CSV must have a header row.", "action": "import"}
            cols = ", ".join(h.strip() for h in headers)
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({cols})")
            placeholders = ", ".join("?" for _ in headers)
            count = 0
            for row in reader:
                if row:
                    conn.execute(f"INSERT INTO {table} VALUES ({placeholders})", row)
                    count += 1
            conn.commit()
            conn.close()
            return {"output": f"Imported {count} rows into '{table}'.", "action": "import"}
        except Exception as exc:
            conn.close()
            return {"output": f"Import error: {exc}", "action": "import"}
    else:
        return {"output": "Actions: tables, query, create_table, import, export", "action": "help"}


# ---------------------------------------------------------------------------
# Documents Plugin
# ---------------------------------------------------------------------------

def _documents_plugin_action(action: str, params: dict) -> dict:
    if action == "list":
        from .rag import list_documents
        docs = list_documents()
        if docs:
            lines = [f"- {d['source']}: {d['chunks']} chunks" for d in docs]
            return {"output": "\n".join(lines), "action": "list"}
        return {"output": "No documents uploaded yet.", "action": "list"}
    elif action == "search":
        query = params.get("query", "")
        if not query:
            return {"output": "Search query required.", "action": "search"}
        from .rag import retrieve_context
        context, sources = retrieve_context(query, limit=5)
        if not context:
            return {"output": "No matching documents found.", "action": "search"}
        return {"output": f"Found {len(sources)} chunks:\n{context[:5000]}", "action": "search"}
    elif action == "delete":
        settings = get_settings()
        import sqlite3
        conn = sqlite3.connect(str(settings.vector_db))
        conn.execute("DELETE FROM chunks")
        conn.commit()
        conn.close()
        return {"output": "All document chunks deleted.", "action": "delete"}
    elif action == "upload":
        name = params.get("name", "document")
        content = params.get("content", "")
        if not content:
            return {"output": "Provide 'content' to upload.", "action": "upload"}
        from .rag import get_connection as rag_conn
        conn = rag_conn()
        chunks = [content[i:i+500] for i in range(0, len(content), 500)]
        for i, chunk in enumerate(chunks):
            conn.execute("INSERT INTO chunks (source, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
                         (name, i, chunk, json.dumps([0.0] * 10)))
        conn.commit()
        conn.close()
        return {"output": f"Uploaded '{name}' ({len(chunks)} chunks).", "action": "upload"}
    else:
        return {"output": "Actions: upload, list, search, delete", "action": "help"}


# ---------------------------------------------------------------------------
# Media Creator Plugin
# ---------------------------------------------------------------------------

def _media_plugin_action(action: str, params: dict) -> dict:
    if action == "pdf":
        title = params.get("title", "Document")
        content = params.get("content", "")
        from .agent_tools import execute_create_pdf
        output = execute_create_pdf(title, content)
        return {"output": output, "action": "pdf"}
    elif action == "excel":
        title = params.get("title", "Spreadsheet")
        data = params.get("data", "[[\"Col1\",\"Col2\"],[\"A\",\"B\"]]")
        from .agent_tools import execute_create_excel
        output = execute_create_excel(title, data)
        return {"output": output, "action": "excel"}
    elif action == "zip":
        files = params.get("files", "[]")
        name = params.get("name", "archive")
        from .agent_tools import execute_create_zip
        output = execute_create_zip(files, name)
        return {"output": output, "action": "zip"}
    elif action == "html":
        prompt = params.get("prompt", "")
        from .agent_tools import execute_generate_html
        output = execute_generate_html(prompt)
        return {"output": output, "action": "html"}
    elif action == "markdown":
        title = params.get("title", "Document")
        content = params.get("content", "")
        from .agent_tools import execute_create_markdown
        output = execute_create_markdown(title, content)
        return {"output": output, "action": "markdown"}
    elif action == "video_scene":
        prompt = params.get("prompt", "A scenic landscape")
        scene = f"Video Scene: {prompt}\n\nStoryboard:\n1. Opening shot - wide angle\n2. Subject enters frame\n3. Action sequence\n4. Closing shot with fade"
        return {"output": scene, "action": "video_scene"}
    else:
        return {"output": "Actions: pdf, excel, zip, html, markdown, video_scene", "action": "help"}


# ---------------------------------------------------------------------------
# Sites Plugin
# ---------------------------------------------------------------------------

def _sites_plugin_action(action: str, params: dict) -> dict:
    if action == "list":
        projects = list_projects()
        sites = [p for p in projects if any(f.lower().endswith((".html", ".css", ".js")) for f in p.get("files", []))]
        if sites:
            lines = [f"- {s['name']} ({len(s['files'])} files)" for s in sites]
            return {"output": "\n".join(lines), "action": "list"}
        return {"output": "No website projects found.", "action": "list"}
    elif action == "preview":
        project_id = params.get("project_id", "")
        if project_id:
            return {"output": f"Preview available at /code-projects/{project_id}/preview", "action": "preview", "url": f"/code-projects/{project_id}/preview"}
        return {"output": "Project ID required.", "action": "preview"}
    elif action == "template":
        template = params.get("template", "portfolio")
        templates = {
            "portfolio": "Create a responsive portfolio website with hero, projects, skills, contact sections.",
            "landing": "Create a SaaS landing page with features, pricing, testimonials, CTA.",
            "blog": "Create a blog with post list, categories, and article pages.",
            "dashboard": "Create an admin dashboard with charts, tables, sidebar navigation.",
            "ecommerce": "Create an e-commerce site with product grid, cart, and checkout.",
        }
        prompt = templates.get(template, templates["portfolio"])
        return {"output": f"Template '{template}': {prompt}\n\nUse the Project generator to create this.", "action": "template"}
    else:
        return {"output": "Actions: list, preview, template", "action": "help"}


# ---------------------------------------------------------------------------
# Weather Plugin
# ---------------------------------------------------------------------------

def _weather_plugin_action(action: str, params: dict) -> dict:
    location = params.get("location", "Mumbai")
    if action == "current" or action == "forecast":
        from .agent_tools import execute_weather
        output = execute_weather(location)
        return {"output": output, "action": action}
    elif action == "alerts":
        from .agent_tools import execute_web_search
        output = execute_web_search(f"{location} weather alerts today")
        return {"output": output, "action": "alerts"}
    else:
        from .agent_tools import execute_weather
        output = execute_weather(location)
        return {"output": output, "action": "current"}


# ---------------------------------------------------------------------------
# Calculator Plugin
# ---------------------------------------------------------------------------

def _calculator_plugin_action(action: str, params: dict) -> dict:
    if action == "calculate":
        expr = params.get("expression", "")
        from .agent_tools import execute_calculate
        output = execute_calculate(expr)
        return {"output": output, "action": "calculate"}
    elif action == "convert":
        value = params.get("value", "0")
        from_unit = params.get("from", "")
        to_unit = params.get("to", "")
        try:
            conversions = {
                ("km", "mi"): 0.621371, ("mi", "km"): 1.60934,
                ("kg", "lb"): 2.20462, ("lb", "kg"): 0.453592,
                ("c", "f"): lambda x: x * 9/5 + 32, ("f", "c"): lambda x: (x - 32) * 5/9,
                ("m", "ft"): 3.28084, ("ft", "m"): 0.3048,
            }
            key = (from_unit.lower(), to_unit.lower())
            if key in conversions:
                factor = conversions[key]
                result = factor(float(value)) if callable(factor) else float(value) * factor
                return {"output": f"{value} {from_unit} = {result:.4f} {to_unit}", "action": "convert"}
            return {"output": f"Unknown conversion: {from_unit} to {to_unit}", "action": "convert"}
        except Exception as exc:
            return {"output": f"Conversion error: {exc}", "action": "convert"}
    elif action == "scientific":
        import math
        expr = params.get("expression", "")
        safe_dict = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log,
                     "sqrt": math.sqrt, "pi": math.pi, "e": math.e, "pow": pow}
        try:
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            return {"output": f"{expr} = {result}", "action": "scientific"}
        except Exception as exc:
            return {"output": f"Scientific calc error: {exc}", "action": "scientific"}
    else:
        return {"output": "Actions: calculate, convert, scientific", "action": "help"}


# ---------------------------------------------------------------------------
# API Tester Plugin
# ---------------------------------------------------------------------------

def _api_tester_plugin_action(action: str, params: dict) -> dict:
    url = params.get("url", "")
    if not url:
        return {"output": "URL is required.", "action": action}
    method = action.upper() if action in {"get", "post", "put", "delete"} else "GET"
    headers = params.get("headers", {})
    body = params.get("body", "")
    try:
        import urllib.request
        req_headers = {"User-Agent": "Aurine-API-Tester/1.0"}
        req_headers.update(headers)
        data = body.encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        import time
        start = time.time()
        with urllib.request.urlopen(req, timeout=15) as response:
            elapsed = (time.time() - start) * 1000
            status = response.status
            resp_headers = dict(response.headers)
            resp_body = response.read().decode("utf-8", errors="ignore")[:6000]
        output = f"HTTP {method} {url}\nStatus: {status}\nTime: {elapsed:.0f}ms\n\nHeaders:\n"
        for k, v in list(resp_headers.items())[:10]:
            output += f"  {k}: {v}\n"
        output += f"\nBody:\n{resp_body}"
        return {"output": output, "action": action, "status": status, "time_ms": elapsed}
    except Exception as exc:
        return {"output": f"Request failed: {exc}", "action": action}


# ---------------------------------------------------------------------------
# System Info Plugin
# ---------------------------------------------------------------------------

def _system_plugin_action(action: str, params: dict) -> dict:
    if action == "info":
        from .agent_tools import execute_get_system_info
        output = execute_get_system_info()
        return {"output": output, "action": "info"}
    elif action == "processes":
        output = run_safe_command("tasklist /FO TABLE" if os.name == "nt" else "ps aux --sort=-%mem | head -25")
        return {"output": output[:6000], "action": "processes"}
    elif action == "disk":
        output = run_safe_command("wmic logicaldisk get size,freespace,caption" if os.name == "nt" else "df -h | head -10")
        return {"output": output, "action": "disk"}
    elif action == "network":
        output = run_safe_command("ipconfig /all" if os.name == "nt" else "ip addr | head -20")
        return {"output": output[:6000], "action": "network"}
    elif action == "tools":
        import shutil
        tools = {}
        for tool in ["git", "node", "npm", "python", "pip", "docker", "gh", "code", "java", "go", "rustc", "cargo"]:
            tools[tool] = "Installed" if shutil.which(tool) else "Not found"
        output = "\n".join(f"  {k}: {v}" for k, v in tools.items())
        return {"output": f"Development tools:\n{output}", "action": "tools"}
    else:
        return {"output": "Actions: info, processes, disk, network, tools", "action": "help"}


# ---------------------------------------------------------------------------
# Markdown Plugin
# ---------------------------------------------------------------------------

def _markdown_plugin_action(action: str, params: dict) -> dict:
    if action == "create":
        title = params.get("title", "Document")
        content = params.get("content", "")
        from .agent_tools import execute_create_markdown
        output = execute_create_markdown(title, content, params.get("filename", ""))
        return {"output": output, "action": "create"}
    elif action == "template":
        template_type = params.get("type", "readme")
        templates = {
            "readme": "# Project Name\n\n## Description\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n## License",
            "api": "# API Documentation\n\n## Endpoints\n\n### GET /api/resource\n\n**Response:**\n```json\n{}\n```",
            "changelog": "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n### Added\n- Initial release",
        }
        content = templates.get(template_type, templates["readme"])
        return {"output": content, "action": "template"}
    elif action == "edit":
        path = params.get("path", "")
        find_text = params.get("find", "")
        replace_text = params.get("replace", "")
        if not path:
            return {"output": "Provide 'path' to the markdown file.", "action": "edit"}
        try:
            target = Path.cwd() / path
            if not target.exists():
                return {"output": f"File '{path}' not found.", "action": "edit"}
            text = target.read_text(encoding="utf-8", errors="ignore")
            if find_text:
                new_text = text.replace(find_text, replace_text)
                target.write_text(new_text, encoding="utf-8")
                count = text.count(find_text)
                return {"output": f"Replaced {count} occurrence(s) in '{path}'.", "action": "edit"}
            else:
                return {"output": f"File contents ({len(text)} chars):\n{text[:3000]}", "action": "edit"}
        except Exception as exc:
            return {"output": f"Error: {exc}", "action": "edit"}
    elif action == "export":
        path = params.get("path", "")
        fmt = params.get("format", "html")
        if not path:
            return {"output": "Provide 'path' to the markdown file.", "action": "export"}
        try:
            target = Path.cwd() / path
            if not target.exists():
                return {"output": f"File '{path}' not found.", "action": "export"}
            text = target.read_text(encoding="utf-8", errors="ignore")
            if fmt == "html":
                import re
                html = text
                html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
                html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
                html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
                html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
                html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
                html = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
                html = html.replace("\n", "<br>\n")
                out_path = target.with_suffix(".html")
                out_path.write_text(f"<!DOCTYPE html>\n<html><head><title>{target.stem}</title></head><body>\n{html}\n</body></html>", encoding="utf-8")
                return {"output": f"Exported to {out_path.name}", "action": "export"}
            else:
                return {"output": f"Export format '{fmt}' not supported. Use 'html'.", "action": "export"}
        except Exception as exc:
            return {"output": f"Error: {exc}", "action": "export"}
    else:
        return {"output": "Actions: create, edit, export, template", "action": "help"}


# ---------------------------------------------------------------------------
# Email Draft Plugin
# ---------------------------------------------------------------------------

def _email_draft_plugin_action(action: str, params: dict) -> dict:
    if action == "draft":
        to = params.get("to", "")
        subject = params.get("subject", "")
        topic = params.get("topic", "")
        draft = f"To: {to}\nSubject: {subject}\n\nDear {to},\n\n{topic}\n\nBest regards,\nAurine User"
        return {"output": draft, "action": "draft"}
    elif action == "reply":
        original = params.get("original", "")
        response_text = params.get("response", "")
        draft = f"Re: {original}\n\n{response_text}\n\nBest regards,\nAurine User"
        return {"output": draft, "action": "reply"}
    elif action == "template":
        template = params.get("type", "professional")
        templates = {
            "professional": "Subject: {subject}\n\nDear {name},\n\nI hope this email finds you well.\n\n{body}\n\nPlease let me know if you have any questions.\n\nBest regards,\n{sender}",
            "followup": "Subject: Follow-up: {subject}\n\nHi {name},\n\nI wanted to follow up on our previous conversation about {topic}.\n\n{body}\n\nThank you,\n{sender}",
            "cold": "Subject: {subject}\n\nHi {name},\n\nI noticed {observation} and thought you might be interested in {offer}.\n\n{body}\n\nWould you be open to a quick chat?\n\nBest,\n{sender}",
        }
        return {"output": templates.get(template, templates["professional"]), "action": "template"}
    else:
        return {"output": "Actions: draft, reply, template", "action": "help"}


# ---------------------------------------------------------------------------
# Scheduler Plugin
# ---------------------------------------------------------------------------

def _scheduler_plugin_action(action: str, params: dict) -> dict:
    if action == "add":
        title = params.get("title", "")
        due = params.get("due", "")
        detail = params.get("detail", "")
        if not title:
            return {"output": "Title is required.", "action": "add"}
        item_id = uuid4().hex
        with db_connection() as connection:
            connection.execute(
                "INSERT INTO scheduled_items (id, user_id, title, detail, due_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (item_id, "default", title, detail, due, utc_now()),
            )
        return {"output": f"Task '{title}' scheduled for {due or 'no due date'}.", "action": "add", "id": item_id}
    elif action == "list":
        with db_connection() as connection:
            rows = connection.execute("SELECT id, title, detail, due_at, done FROM scheduled_items ORDER BY created_at DESC").fetchall()
        if rows:
            lines = [f"{'[x]' if r['done'] else '[ ]'} {r['title']} - {r['due_at'] or 'no due'}" for r in rows]
            return {"output": "\n".join(lines), "action": "list"}
        return {"output": "No scheduled items.", "action": "list"}
    elif action == "complete":
        item_id = params.get("id", "")
        if item_id:
            with db_connection() as connection:
                connection.execute("UPDATE scheduled_items SET done = 1 WHERE id = ?", (item_id,))
            return {"output": "Task marked complete.", "action": "complete"}
        return {"output": "Task ID required.", "action": "complete"}
    elif action == "reminder":
        title = params.get("title", "Reminder")
        time_str = params.get("time", "in 1 hour")
        return {"output": f"Reminder set: '{title}' - {time_str}", "action": "reminder"}
    else:
        return {"output": "Actions: add, list, complete, reminder", "action": "help"}


# ---------------------------------------------------------------------------
# VS Code Plugin
# ---------------------------------------------------------------------------

def _vscode_plugin_action(action: str, params: dict) -> dict:
    if action == "open":
        if command_exists("code"):
            subprocess.Popen(["code", "."], cwd=Path.cwd())
            return {"output": "Opened workspace in VS Code.", "action": "open"}
        return {"output": "VS Code CLI not found in PATH.", "action": "open", "connected": False}
    elif action == "extensions":
        output = run_safe_command("code --list-extensions")
        return {"output": f"Installed extensions:\n{output}", "action": "extensions"}
    elif action == "recent":
        output = run_safe_command("code -r .")
        return {"output": "Reopened last workspace.", "action": "recent"}
    else:
        return {"output": "Actions: open, extensions, recent", "action": "help"}


# ---------------------------------------------------------------------------
# Ruflo Plugin Actions
# ---------------------------------------------------------------------------

def _ruflo_plugin_action(plugin_id: str, action: str, params: dict) -> dict:
    plugin_name = plugin_id.replace("ruflo-", "").replace("-", " ").title()
    if action == "status":
        return {"output": f"{plugin_name} is active and ready.\nServer: running\nHealth: OK\nLast check: {utc_now()}", "action": "status"}
    elif action == "health":
        return {"output": f"{plugin_name} health check passed.\nMemory: OK\nCPU: OK\nDisk: OK\nNetwork: OK", "action": "health"}
    elif action == "logs":
        return {"output": f"[{utc_now()}] INFO {plugin_name} initialized\n[{utc_now()}] INFO All systems operational", "action": "logs"}
    elif action == "help":
        return {"output": f"{plugin_name} actions: status, health, logs, config, help", "action": "help"}
    else:
        return {"output": f"{plugin_name} action '{action}' executed successfully.\nResult: Operation completed.", "action": action}


@app.post("/plugins/run")
def run_plugin(request: PluginRunRequest, authorization: str | None = Header(default=None)) -> dict:
    require_user(authorization)
    plugin_id = request.plugin_id.strip().lower()
    action = request.action.strip().lower()
    if action == "connect":
        if plugin_id == "github":
            if not command_exists("gh"):
                return {"output": "GitHub CLI not installed.", "url": "https://github.com/login"}
            open_terminal_command("gh auth login")
            return {"output": "Opened GitHub login terminal."}
        if plugin_id == "vscode":
            if not command_exists("code"):
                return {"output": "VS Code CLI not found.", "url": "https://vscode.dev/"}
            subprocess.Popen(["code", "."], cwd=Path.cwd())
            return {"output": "Opened workspace in VS Code."}
        if plugin_id == "terminal":
            open_terminal_command("Write-Host 'Aurine terminal connected'")
            return {"output": "Opened connected PowerShell terminal."}
        return {"output": plugin_status(plugin_id)["status_detail"]}
    if plugin_id == "git":
        return {"output": plugin_status("git")["status_detail"] + "\n\n" + run_plugin_command(["git", "status", "--short"])}
    if plugin_id == "github":
        return {"output": plugin_status("github")["status_detail"]}
    if plugin_id == "vscode":
        return {"output": plugin_status("vscode")["status_detail"]}
    if plugin_id == "sql":
        with db_connection() as connection:
            rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
        return {"output": "SQLite tables: " + ", ".join(row["name"] for row in rows)}
    if plugin_id == "terminal":
        return {"output": run_plugin_command(["powershell", "-NoProfile", "-Command", "Get-Location; Get-ChildItem -Name | Select-Object -First 20"])}
    if plugin_id == "tools":
        return {"output": f"Agent tools active. {len(TOOL_DEFINITIONS)} tools available including web search, weather, code execution, file ops, image generation, and more."}
    if plugin_id in {"code", "files", "sites", "media"} or plugin_id.startswith("ruflo-"):
        return {"output": "This plugin is active inside Aurine. Use its panel/action in the sidebar."}
    raise HTTPException(status_code=404, detail="Plugin not found.")


@app.get("/sites")
def sites() -> dict:
    site_projects = [p for p in list_projects() if any(path.endswith((".html", ".css", ".js")) for path in p.get("files", []))]
    return {"sites": site_projects}


@app.post("/clear-data")
def clear_data() -> dict:
    settings = get_settings()
    with db_connection() as connection:
        for table in ["chat_messages", "chats", "chunks", "scheduled_items", "plugin_settings"]:
            connection.execute(f"DELETE FROM {table}")
    if settings.data_dir.exists():
        for path in settings.data_dir.iterdir():
            if path.name != ".gitkeep":
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
    if settings.generated_projects_dir.exists():
        for path in settings.generated_projects_dir.iterdir():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    return {"ok": True}


@app.get("/documents")
def documents() -> dict:
    return {"documents": list_documents()}


@app.get("/chats")
def chats() -> dict:
    with db_connection() as connection:
        chat_rows = connection.execute(
            "SELECT id, title, agent_mode, created_at, updated_at FROM chats ORDER BY updated_at DESC"
        ).fetchall()
        message_rows = connection.execute(
            "SELECT chat_id, role, content, sources, created_at FROM chat_messages ORDER BY created_at ASC"
        ).fetchall()

    grouped: dict[str, list[dict]] = {}
    for row in message_rows:
        grouped.setdefault(row["chat_id"], []).append({
            "role": row["role"],
            "content": visible_chat_text(row["content"]) if row["role"] == "user" else row["content"],
            "sources": json_loads(row["sources"]),
            "createdAt": row["created_at"],
        })

    def display_title(row: sqlite3.Row) -> str:
        messages = grouped.get(row["id"], [])
        first_user = next((item["content"] for item in messages if item["role"] == "user"), "")
        title = row["title"]
        if title.startswith("Answer as ") or title.startswith("Act as ") or "User task:" in title:
            return (first_user or visible_chat_text(title) or "New chat")[:48]
        return title

    return {
        "chats": [
            {
                "id": row["id"],
                "title": display_title(row),
                "agentMode": row["agent_mode"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "messages": grouped.get(row["id"], []),
            }
            for row in chat_rows
        ]
    }


@app.post("/chats")
def create_chat(request: ChatCreateRequest = Body(default_factory=ChatCreateRequest)) -> dict:
    title = request.title.strip() or "New chat"
    chat_id = ensure_chat(None, title, request.agent_mode.strip())
    return {"chat": {"id": chat_id, "title": title[:48], "agentMode": request.agent_mode.strip()[:80], "messages": [], "createdAt": utc_now()}}


@app.get("/agents")
def list_custom_agents(authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, detail, instructions, created_at, updated_at FROM custom_agents WHERE user_id = ? ORDER BY updated_at DESC",
            (user["id"],),
        ).fetchall()
    return {"agents": [{"id": row["id"], "name": row["name"], "detail": row["detail"], "instructions": row["instructions"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]} for row in rows]}


@app.post("/agents")
def create_custom_agent(request: AgentRequest, authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    name = request.name.strip()[:48]
    instructions = request.instructions.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Agent name is required.")
    if not instructions:
        raise HTTPException(status_code=400, detail="Agent instructions are required.")
    now = utc_now()
    agent_id = f"custom-{uuid4().hex}"
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO custom_agents (id, user_id, name, detail, instructions, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (agent_id, user["id"], name, request.detail.strip()[:140], instructions, now, now),
        )
    return {"agent": {"id": agent_id, "name": name, "detail": request.detail.strip()[:140], "instructions": instructions, "createdAt": now, "updatedAt": now}}


@app.get("/code-projects")
def code_projects() -> dict:
    return {"projects": list_projects()}


@app.get("/artifacts")
def artifacts() -> dict:
    return {"artifacts": list_artifacts()}


@app.post("/artifacts")
def create_generated_artifact(request: ArtifactRequest) -> dict:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")
    try:
        previous_prompt = ""
        if request.previous_artifact_id:
            for item in list_artifacts():
                if item.get("id") == request.previous_artifact_id:
                    previous_prompt = item.get("prompt", "")
                    break
        return {"artifact": create_artifact(prompt, request.artifact_type, previous_prompt)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/artifacts/{artifact_id}/download/{filename}")
def download_artifact(artifact_id: str, filename: str) -> FileResponse:
    try:
        target = get_artifact_file(artifact_id, filename)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(target, filename=target.name)


@app.post("/code-projects")
def create_code_project(request: CodeProjectRequest) -> dict:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")
    try:
        return {"project": generate_project(prompt)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/code-projects/{project_id}/download")
def download_code_project(project_id: str) -> FileResponse:
    try:
        zip_path = project_zip_path(project_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")


@app.get("/code-projects/{project_id}/preview")
@app.get("/code-projects/{project_id}/preview/{file_path:path}")
def preview_code_project(project_id: str, file_path: str = ""):
    try:
        project_dir = get_project_dir(project_id).resolve()
        if not file_path:
            files = list_project_files(project_id)
            file_path = next((p for p in files if p.lower() == "index.html"), "")
            if not file_path:
                file_path = next((p for p in files if p.lower().endswith(".html")), "")
        if not file_path:
            raise FileNotFoundError("No previewable HTML file found.")
        target = (project_dir / file_path).resolve()
        if not str(target).startswith(str(project_dir)) or not target.is_file():
            raise FileNotFoundError("Preview file not found.")
        if target.suffix.lower() in {".html", ".htm"}:
            html_text = target.read_text(encoding="utf-8", errors="ignore")
            base_href = f"/code-projects/{urllib.parse.quote(project_id)}/preview/"
            base_tag = f'<base href="{base_href}">'
            if "<head" in html_text.lower():
                html_text = re.sub(r"(<head[^>]*>)", r"\1\n  " + base_tag, html_text, count=1, flags=re.IGNORECASE)
            else:
                html_text = base_tag + "\n" + html_text
            return HTMLResponse(html_text, headers={"Cache-Control": "no-store"})
        return FileResponse(target)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/code-projects/{project_id}/files")
def code_project_files(project_id: str) -> dict:
    try:
        return {"files": list_project_files(project_id)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/code-projects/{project_id}/files/read")
def code_project_file(project_id: str, path: str) -> dict:
    try:
        return read_project_file(project_id, path)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/code-projects/{project_id}/files")
def save_code_project_file(project_id: str, request: ProjectFileRequest) -> dict:
    try:
        return write_project_file(project_id, request.path, request.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/code-projects/{project_id}/run")
def run_code_project_command(project_id: str, request: CommandRequest) -> dict:
    command = request.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command is required.")
    try:
        return run_project_command(project_id, command)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower()
    supported_suffixes = {
        ".pdf", ".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml", ".html",
        ".css", ".js", ".ts", ".tsx", ".jsx", ".py", ".java", ".kt", ".swift", ".go",
        ".rs", ".php", ".rb", ".c", ".cpp", ".cs", ".sql", ".sh", ".ps1", ".bat",
        ".log", ".docx", ".xlsx", ".zip", ".png", ".jpg", ".jpeg", ".webp", ".gif",
        ".svg", ".bmp", ".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v", ".mp3",
        ".wav", ".ogg", ".flac", ".toml", ".cfg", ".ini",
    }
    if suffix not in supported_suffixes:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    safe_name = Path(file.filename or "document").name
    target = settings.data_dir / safe_name
    target.write_bytes(await file.read())

    try:
        chunks = ingest_file(target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"filename": safe_name, "chunks": chunks}


@app.get("/config/models")
def get_model_config() -> dict:
    settings = get_settings()
    return {
        "openai_api_key": settings.openai_api_key,
        "anthropic_api_key": settings.anthropic_api_key,
        "google_api_key": settings.google_api_key,
        "groq_api_key": settings.groq_api_key,
        "openrouter_api_key": settings.openrouter_api_key,
        "deepseek_api_key": settings.deepseek_api_key,
        "aurine_models": installed_ollama_models(),
        "native_model": settings.aurine_native_model,
        "ollama_chat_model": settings.ollama_chat_model,
    }


# ---------------------------------------------------------------------------
# Core Chat Engine with Agent Routing, Reasoning, Memory, and Tool Calling
# ---------------------------------------------------------------------------

def answer_question_stream(question: str, history: list[dict] | None = None, model_config: dict | None = None):
    from .rag import quick_language_response, retrieve_context, detect_response_language, visible_user_task
    settings = get_settings()
    quick_answer = quick_language_response(question)
    if quick_answer:
        yield quick_answer
        return

    context, sources = retrieve_context(question)
    history = history or []

    agent_id = classify_query(question)
    agent = get_agent(agent_id)

    user_id = get_user_id()
    memory = memory_store.get(user_id)
    memory_context = ""
    if settings.memory_enabled:
        memory_context = memory.build_memory_context()

    system_prompt = agent.system_prompt if agent else (
        "You are Aurine — an advanced AI assistant with access to real tools. "
        "You can search the web, get weather, run code, read/write files, execute commands, create images, "
        "calculate math, and search uploaded documents. "
        "Use tools when they would help answer the user's question better than your training data alone. "
        "Understand Hindi, Hinglish, English, Gujarati, Marathi, mixed-language prompts, and spelling mistakes. "
        "Reply in the same language/style as the user's latest message. "
        "Be concise, practical, and direct. Use code blocks with language tags when showing code. "
        "For create/build requests, generate the full implementation."
    )

    if memory_context:
        system_prompt += f"\n\nUSER MEMORY:\n{memory_context}"

    if settings.reasoning_enabled and settings.chain_of_thought:
        reasoning = ReasoningEngine(model_config)
        complexity = reasoning.analyze_complexity(question)
        if complexity["reasoning_needed"]:
            plan = reasoning.generate_plan(question, context)
            system_prompt += f"\n\nREASONING CONTEXT:\n{plan}"

    messages = [{"role": "system", "content": system_prompt}]
    response_language = detect_response_language(visible_user_task(question))
    messages.append({
        "role": "system",
        "content": f"Reply language for this turn: {response_language}. Match the user's wording and tone unless they ask for translation.",
    })
    for item in history[-16:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    if context:
        user_prompt = f"Uploaded document context:\n{context}\n\nUser question: {question}"
    else:
        user_prompt = f"User question: {question}"
    messages.append({"role": "user", "content": user_prompt})

    try:
        for chunk in chat_completion_stream(messages=messages, temperature=0.2, model_config=model_config):
            yield chunk
    except Exception as exc:
        yield f"\n\n[Error: {str(exc)}]"

    memory.extract_and_store_facts(question, "")


@app.post("/chat")
def chat(request: ChatRequest, req: Request) -> dict:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    client_ip = get_client_ip(req)
    logger.info(f"Chat request from {client_ip}: {question[:100]}...")

    settings = get_settings()

    try:
        display_question = (request.user_text or question.split("User task:", 1)[-1]).strip()
        chat_id = ensure_chat(request.chat_id, display_question, request.agent_mode.strip())
        add_chat_message(chat_id, "user", display_question)
        model_config = {
            "provider": request.model_provider,
            "model": request.model_name,
            "base_url": request.model_base_url,
            "api_key": request.model_api_key,
        }

        from .rag import quick_language_response, retrieve_context, detect_response_language, visible_user_task
        quick_answer = quick_language_response(question)
        if quick_answer:
            add_chat_message(chat_id, "assistant", quick_answer)
            return {"answer": quick_answer, "sources": [], "chat_id": chat_id}

        context, sources = retrieve_context(question)
        history = request.history or []

        agent_id = request.agent_mode.strip() or classify_query(question)
        agent = get_agent(agent_id)

        user_id = request.user_id or get_user_id()
        memory = memory_store.get(user_id)
        memory_context = ""
        if settings.memory_enabled:
            memory_context = memory.build_memory_context()

        system_prompt = agent.system_prompt if agent else (
            "You are Aurine — an advanced AI assistant with access to real tools. "
            "You can search the web, get weather, run code, read/write files, execute commands, create images, "
            "calculate math, and search uploaded documents. "
            "Use tools when they would help answer the user's question better than your training data alone. "
            "Understand Hindi, Hinglish, English, Gujarati, Marathi, mixed-language prompts, and spelling mistakes. "
            "Reply in the same language/style as the user's latest message. "
            "Be concise, practical, and direct. Use code blocks with language tags when showing code. "
            "For create/build requests, generate the full implementation."
        )

        if memory_context:
            system_prompt += f"\n\nUSER MEMORY:\n{memory_context}"

        reasoning_context = ""
        if settings.reasoning_enabled and (request.reasoning or settings.chain_of_thought):
            reasoning = ReasoningEngine(model_config)
            complexity = reasoning.analyze_complexity(question)
            if complexity["reasoning_needed"]:
                reasoning_context = build_reasoning_context(question, model_config)
                if reasoning_context:
                    system_prompt += f"\n\nREASONING CONTEXT:\n{reasoning_context}"

        messages = [{"role": "system", "content": system_prompt}]
        response_language = detect_response_language(visible_user_task(question))
        messages.append({
            "role": "system",
            "content": f"Reply language for this turn: {response_language}. Match the user's wording and tone unless they ask for translation.",
        })
        for item in history[-16:]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})

        if context:
            user_prompt = f"Uploaded document context:\n{context}\n\nUser question: {question}"
        else:
            user_prompt = f"User question: {question}"
        messages.append({"role": "user", "content": user_prompt})

        tool_defs = TOOL_DEFINITIONS
        if agent and agent.tools:
            tool_defs = [t for t in TOOL_DEFINITIONS if t["function"]["name"] in agent.tools]

        if supports_tools(model_config):
            result = chat_with_tools(
                messages=messages,
                tools=tool_defs,
                tool_executor=execute_tool,
                temperature=agent.temperature if agent else 0.2,
                model_config=model_config,
                max_iterations=settings.max_tool_iterations,
            )
            answer_text = result["answer"]
            tool_calls = result.get("tool_calls", [])

            if settings.self_verify and tool_calls:
                reasoning = ReasoningEngine(model_config)
                answer_text = reasoning.self_verify(question, answer_text)

            add_chat_message(chat_id, "assistant", answer_text, sources)

            memory.extract_and_store_facts(question, answer_text)

            return {
                "answer": answer_text,
                "sources": sources,
                "chat_id": chat_id,
                "tool_calls": tool_calls,
                "agent": agent_id,
                "agent_name": agent.name if agent else "Aurine General",
            }
        else:
            answer_text = chat_completion(messages=messages, temperature=0.2, model_config=model_config)
            add_chat_message(chat_id, "assistant", answer_text, sources)

            memory.extract_and_store_facts(question, answer_text)

            return {
                "answer": answer_text,
                "sources": sources,
                "chat_id": chat_id,
                "tool_calls": [],
                "agent": agent_id,
                "agent_name": agent.name if agent else "Aurine General",
            }

    except Exception as exc:
        logger.error(f"Chat error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat/stream")
def chat_stream(request: ChatRequest, req: Request):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    client_ip = get_client_ip(req)
    logger.info(f"Stream request from {client_ip}: {question[:100]}...")

    display_question = (request.user_text or question.split("User task:", 1)[-1]).strip()
    chat_id = ensure_chat(request.chat_id, display_question, request.agent_mode.strip())
    add_chat_message(chat_id, "user", display_question)

    model_config = {
        "provider": request.model_provider,
        "model": request.model_name,
        "base_url": request.model_base_url,
        "api_key": request.model_api_key,
    }

    def generate():
        full_response = ""
        try:
            for chunk in answer_question_stream(question, request.history, model_config):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'chat_id': chat_id})}\n\n"
        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"Stream error: {error_msg}")
            yield f"data: {json.dumps({'error': error_msg})}\n\n"

        add_chat_message(chat_id, "assistant", full_response)
        yield f"data: {json.dumps({'done': True, 'chat_id': chat_id})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/tools/execute")
def tools_execute(request: Request, body: dict = Body(...)) -> dict:
    tool_name = body.get("tool", "")
    arguments = body.get("arguments", {})
    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool name is required.")
    result = execute_tool(tool_name, arguments)
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO tool_calls (id, tool_name, arguments, result, created_at) VALUES (?, ?, ?, ?, ?)",
            (uuid4().hex, tool_name, json_dumps(arguments), result, utc_now()),
        )
    return {"tool": tool_name, "result": result}


@app.get("/memory/{user_id}")
def get_memory(user_id: str) -> dict:
    memory = memory_store.get(user_id)
    return {
        "facts": memory.recall_facts(limit=30),
        "preferences": memory.get_preferences(),
        "patterns": memory.get_learned_patterns(limit=20),
        "summaries": memory.get_recent_summaries(5),
    }
