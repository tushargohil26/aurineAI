import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Generator


def _read_env():
    env = {}
    for p in [".env", os.path.expanduser("~/.aurine/.env")]:
        if os.path.exists(p):
            with open(p) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in env.items():
        if k not in os.environ or not os.environ[k]:
            os.environ[k] = v
    return env


_env = _read_env()


def _g(key, default=""):
    return os.environ.get(key, _env.get(key, default)).strip()


class Settings:
    ai_provider: str = "aurine"

    google_api_key: str = ""
    google_chat_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-sonnet-4-20250514"
    deepseek_api_key: str = ""
    deepseek_chat_model: str = "deepseek-chat"
    openrouter_api_key: str = ""
    openrouter_chat_model: str = "meta-llama/llama-3.1-405b-instruct"
    mistral_api_key: str = ""
    mistral_chat_model: str = "mistral-large-latest"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5-coder:7b"
    ollama_embedding_model: str = "nomic-embed-text"
    aurine_native_model: str = "qwen2.5-coder:7b"
    aurine_embedding_model: str = "nomic-embed-text"

    vector_db: str = "./vector_store.sqlite3"
    data_dir: Path = Path("./data")
    generated_projects_dir: Path = Path("./generated_projects")

    memory_enabled: bool = True
    reasoning_enabled: bool = True
    chain_of_thought: bool = True
    self_verify: bool = True
    max_tool_iterations: int = 5

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""
    email_from: str = "Aurine <no-reply@aurine.local>"
    otp_ttl_seconds: int = 600

    def __init__(self):
        self.ai_provider = _g("AI_PROVIDER", "aurine")

        self.google_api_key = _g("GOOGLE_API_KEY")
        self.google_chat_model = _g("GOOGLE_CHAT_MODEL", "gemini-2.0-flash")
        self.openai_api_key = _g("OPENAI_API_KEY")
        self.openai_chat_model = _g("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.groq_api_key = _g("GROQ_API_KEY")
        self.groq_chat_model = _g("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
        self.anthropic_api_key = _g("ANTHROPIC_API_KEY")
        self.anthropic_chat_model = _g("ANTHROPIC_CHAT_MODEL", "claude-sonnet-4-20250514")
        self.deepseek_api_key = _g("DEEPSEEK_API_KEY")
        self.deepseek_chat_model = _g("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
        self.openrouter_api_key = _g("OPENROUTER_API_KEY")
        self.openrouter_chat_model = _g("OPENROUTER_CHAT_MODEL", "meta-llama/llama-3.1-405b-instruct")
        self.mistral_api_key = _g("MISTRAL_API_KEY")
        self.mistral_chat_model = _g("MISTRAL_CHAT_MODEL", "mistral-large-latest")

        self.ollama_base_url = _g("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.ollama_chat_model = _g("OLLAMA_CHAT_MODEL", "qwen2.5-coder:7b")
        self.ollama_embedding_model = _g("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self.aurine_native_model = _g("AURINE_NATIVE_MODEL", "qwen2.5-coder:7b")
        self.aurine_embedding_model = _g("AURINE_EMBEDDING_MODEL", "nomic-embed-text")

        self.vector_db = _g("VECTOR_DB", "./vector_store.sqlite3")
        self.data_dir = Path(_g("DATA_DIR", "./data"))
        self.generated_projects_dir = Path(_g("GENERATED_PROJECTS_DIR", "./generated_projects"))

        self.memory_enabled = _g("MEMORY_ENABLED", "true").lower() in ("true", "1", "yes")
        self.reasoning_enabled = _g("REASONING_ENABLED", "true").lower() in ("true", "1", "yes")
        self.chain_of_thought = _g("CHAIN_OF_THOUGHT", "true").lower() in ("true", "1", "yes")
        self.self_verify = _g("SELF_VERIFY", "true").lower() in ("true", "1", "yes")
        self.max_tool_iterations = int(_g("MAX_TOOL_ITERATIONS", "5"))

        self.google_client_id = _g("GOOGLE_CLIENT_ID")
        self.google_client_secret = _g("GOOGLE_CLIENT_SECRET")
        self.google_redirect_uri = _g("GOOGLE_REDIRECT_URI", "")

        self.email_smtp_host = _g("EMAIL_SMTP_HOST")
        self.email_smtp_port = int(_g("EMAIL_SMTP_PORT", "587"))
        self.email_smtp_user = _g("EMAIL_SMTP_USER")
        self.email_smtp_password = _g("EMAIL_SMTP_PASSWORD")
        self.email_from = _g("EMAIL_FROM", "Aurine <no-reply@aurine.local>")
        self.otp_ttl_seconds = int(_g("OTP_TTL_SECONDS", "600"))


_settings_cache = None


def get_settings():
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache


def reload_settings():
    global _settings_cache, _env
    _env = _read_env()
    _settings_cache = Settings()
    return _settings_cache


AURINE_API_URL = "http://localhost:8000"
