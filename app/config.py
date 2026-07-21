from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
import os


load_dotenv()

AURINE_API_URL = "http://localhost:8000"


class Settings(BaseModel):
    ai_provider: str = "aurine"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    mistral_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    fireworks_api_key: str = ""
    nvidia_api_key: str = ""
    cerebras_api_key: str = ""
    sambanova_api_key: str = ""
    aurine_api_url: str = AURINE_API_URL
    aurine_native_model: str = "aurine-coder"
    aurine_embedding_model: str = "nomic-embed-text"
    chat_model: str = "gpt-4o-mini"
    anthropic_chat_model: str = "claude-sonnet-4-20250514"
    google_chat_model: str = "gemini-2.0-flash"
    mistral_chat_model: str = "mistral-large-latest"
    groq_chat_model: str = "llama-3.3-70b-versatile"
    openrouter_chat_model: str = "meta-llama/llama-3.1-405b-instruct"
    deepseek_chat_model: str = "deepseek-chat"
    embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "qwen2.5-coder:7b"
    ollama_embedding_model: str = "nomic-embed-text"
    vector_db: Path = Path("./vector_store.sqlite3")
    data_dir: Path = Path("./data")
    generated_projects_dir: Path = Path("./generated_projects")
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    image_generation_model: str = "dall-e-3"
    image_generation_size: str = "1024x1024"
    rate_limit_per_minute: int = 30
    streaming_enabled: bool = True
    tools_enabled: bool = True
    reasoning_enabled: bool = True
    memory_enabled: bool = True
    auto_agent_routing: bool = True
    max_history_turns: int = 20
    max_tool_iterations: int = 10
    self_verify: bool = False
    chain_of_thought: bool = True


_settings_cache: Settings | None = None


def get_settings() -> Settings:
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache
    _settings_cache = _build_settings()
    return _settings_cache


def reload_settings() -> Settings:
    global _settings_cache
    load_dotenv(override=True)
    _settings_cache = _build_settings()
    return _settings_cache


def _build_settings() -> Settings:
    return Settings(
        ai_provider=os.getenv("AI_PROVIDER", "aurine").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        mistral_api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        fireworks_api_key=os.getenv("FIREWORKS_API_KEY", "").strip(),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", "").strip(),
        cerebras_api_key=os.getenv("CEREBRAS_API_KEY", "").strip(),
        sambanova_api_key=os.getenv("SAMBANOVA_API_KEY", "").strip(),
        aurine_api_url=os.getenv("AURINE_API_URL", AURINE_API_URL).strip(),
        aurine_native_model=os.getenv("AURINE_NATIVE_MODEL", "aurine-coder"),
        aurine_embedding_model=os.getenv("AURINE_EMBEDDING_MODEL", "nomic-embed-text"),
        chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        anthropic_chat_model=os.getenv("ANTHROPIC_CHAT_MODEL", "claude-sonnet-4-20250514"),
        google_chat_model=os.getenv("GOOGLE_CHAT_MODEL", "gemini-2.0-flash"),
        mistral_chat_model=os.getenv("MISTRAL_CHAT_MODEL", "mistral-large-latest"),
        groq_chat_model=os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile"),
        openrouter_chat_model=os.getenv("OPENROUTER_CHAT_MODEL", "meta-llama/llama-3.1-405b-instruct"),
        deepseek_chat_model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5-coder:7b"),
        ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        vector_db=Path(os.getenv("VECTOR_DB", "./vector_store.sqlite3")),
        data_dir=Path(os.getenv("DATA_DIR", "./data")),
        generated_projects_dir=Path(os.getenv("GENERATED_PROJECTS_DIR", "./generated_projects")),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        google_redirect_uri=os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/auth/google/callback",
        ).strip(),
        image_generation_model=os.getenv("IMAGE_GENERATION_MODEL", "dall-e-3"),
        image_generation_size=os.getenv("IMAGE_GENERATION_SIZE", "1024x1024"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")),
        streaming_enabled=os.getenv("STREAMING_ENABLED", "true").lower() == "true",
        tools_enabled=os.getenv("TOOLS_ENABLED", "true").lower() == "true",
        reasoning_enabled=os.getenv("REASONING_ENABLED", "true").lower() == "true",
        memory_enabled=os.getenv("MEMORY_ENABLED", "true").lower() == "true",
        auto_agent_routing=os.getenv("AUTO_AGENT_ROUTING", "true").lower() == "true",
        max_history_turns=int(os.getenv("MAX_HISTORY_TURNS", "20")),
        max_tool_iterations=int(os.getenv("MAX_TOOL_ITERATIONS", "10")),
        self_verify=os.getenv("SELF_VERIFY", "false").lower() == "true",
        chain_of_thought=os.getenv("CHAIN_OF_THOUGHT", "true").lower() == "true",
    )


def require_openai_api_key() -> str:
    api_key = get_settings().openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file or cloud environment variables.")
    return api_key
