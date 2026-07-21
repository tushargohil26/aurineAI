import json
import os
import urllib.request
import urllib.error
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
    ai_provider: str = "google"
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

    def __init__(self):
        self.ai_provider = _g("AI_PROVIDER", "google")
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
