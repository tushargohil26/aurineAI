import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Generator

from openai import OpenAI

from .config import get_settings, reload_settings, AURINE_API_URL

_client_cache: dict[str, OpenAI] = {}

MODELFILE_PATH = Path(__file__).parent.parent / "Modelfile-native"
OLLAMA_SETUP_DONE = Path(__file__).parent.parent / ".aurine_setup_done"


def _ollama_running() -> bool:
    settings = get_settings()
    try:
        req = urllib.request.Request(
            f"{settings.ollama_base_url}/api/tags",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def _ollama_model_exists(model_name: str) -> bool:
    settings = get_settings()
    try:
        req = urllib.request.Request(
            f"{settings.ollama_base_url}/api/tags",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return model_name in models or f"{model_name}:latest" in models
    except Exception:
        return False


def _auto_setup_aurine_model() -> bool:
    if OLLAMA_SETUP_DONE.exists():
        return True

    settings = get_settings()
    model_name = settings.aurine_native_model

    if _ollama_model_exists(model_name):
        OLLAMA_SETUP_DONE.touch()
        return True

    base_model = "qwen2.5-coder:7b"
    if not _ollama_model_exists(base_model):
        print(f"\n  Downloading {base_model} (this may take a few minutes)...")
        try:
            subprocess.run(
                ["ollama", "pull", base_model],
                capture_output=True,
                timeout=600,
                check=True,
            )
        except FileNotFoundError:
            print("  Ollama not found. Install from: https://ollama.com")
            return False
        except subprocess.TimeoutExpired:
            print("  Download timed out. Please run: ollama pull qwen2.5-coder:7b")
            return False
        except subprocess.CalledProcessError:
            print("  Failed to download model. Please run: ollama pull qwen2.5-coder:7b")
            return False

    if MODELFILE_PATH.exists():
        print(f"  Creating Aurine model from Modelfile...")
        try:
            subprocess.run(
                ["ollama", "create", model_name, "-f", str(MODELFILE_PATH)],
                capture_output=True,
                timeout=300,
                check=True,
            )
            OLLAMA_SETUP_DONE.touch()
            print(f"  Aurine model '{model_name}' ready!")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            print(f"  Could not create custom model: {e}")
    else:
        print(f"  Modelfile not found at {MODELFILE_PATH}, using base model directly")

    OLLAMA_SETUP_DONE.touch()
    return True


def _ensure_ollama() -> bool:
    if not _ollama_running():
        return False
    return _auto_setup_aurine_model()


def _aurine_server_running() -> bool:
    try:
        req = urllib.request.Request(
            f"{AURINE_API_URL}/health",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def _auto_fallback_provider() -> tuple[str, str, str]:
    settings = get_settings()
    candidates = [
        ("google", settings.google_chat_model, settings.google_api_key),
        ("groq", settings.groq_chat_model, settings.groq_api_key),
        ("openai", settings.chat_model, settings.openai_api_key),
        ("deepseek", settings.deepseek_chat_model, settings.deepseek_api_key),
        ("anthropic", settings.anthropic_chat_model, settings.anthropic_api_key),
        ("mistral", settings.mistral_chat_model, settings.mistral_api_key),
        ("openrouter", settings.openrouter_chat_model, settings.openrouter_api_key),
        ("cerebras", settings.groq_chat_model, settings.cerebras_api_key),
        ("nvidia", "meta/llama-3.1-405b-instruct", settings.nvidia_api_key),
    ]
    for provider, model, key in candidates:
        if key and len(key.strip()) > 5:
            return provider, model, key
    return "", "", ""


def _aurine_server_post(messages: list[dict], temperature: float = 0.2,
                        stream: bool = False, json_mode: bool = False) -> dict | Generator:
    settings = get_settings()
    payload = {
        "model": "aurine",
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Content-Type": "application/json",
    }

    if stream:
        return _aurine_stream_gen(settings.aurine_api_url, payload, headers)

    request = urllib.request.Request(
        f"{settings.aurine_api_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        choices = data.get("choices", [])
        if choices:
            return {"content": choices[0].get("message", {}).get("content", "")}
        return {"content": ""}
    except Exception as exc:
        raise RuntimeError(f"Aurine server error: {exc}") from exc


def _aurine_stream_gen(url: str, payload: dict, headers: dict) -> Generator[str, None, None]:
    payload["stream"] = True
    request = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for line in response:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        raise RuntimeError(f"Aurine server stream error: {exc}") from exc


def _ollama_post(path: str, payload: dict) -> dict:
    settings = get_settings()
    if not _ollama_running():
        if _aurine_server_running():
            raise _AurineServerFallbackError()
        raise RuntimeError(
            "No AI backend available.\n\n"
            "Ollama is not running. Please:\n"
            "1. Install Ollama: https://ollama.com\n"
            "2. Start Ollama\n"
            "3. Restart Aurine - the model will auto-download\n\n"
            "Or type /connect to set up a cloud provider."
        )
    request = urllib.request.Request(
        f"{settings.ollama_base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Ollama is not running or the model is missing.\n"
            "Start Ollama and the model will auto-download."
        ) from exc


class _OllamaFallbackError(Exception):
    def __init__(self, provider: str, model: str, config: dict):
        self.provider = provider
        self.model = model
        self.config = config
        super().__init__(f"Ollama unavailable, falling back to {provider}:{model}")


class _AurineServerFallbackError(Exception):
    def __init__(self):
        super().__init__("Ollama unavailable, using Aurine server")


def _ollama_stream(path: str, payload: dict) -> Generator[str, None, None]:
    settings = get_settings()
    if not _ollama_running():
        raise RuntimeError(
            "Ollama is not running.\n"
            "Install Ollama from https://ollama.com and restart Aurine."
        )
    request = urllib.request.Request(
        f"{settings.ollama_base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for line in response:
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Ollama is not running or the model is missing.\n"
            "Start Ollama and the model will auto-download."
        ) from exc


def _native_model_name(model: str = "") -> str:
    settings = get_settings()
    requested = (model or "").strip()
    if requested in {"aurine-coder", "aurine-native", "aurine", "default", ""}:
        return settings.aurine_native_model
    return requested


FREE_PROVIDER_URLS = {
    "groq": "https://console.groq.com/keys",
    "openrouter": "https://openrouter.ai/keys",
    "cerebras": "https://cloud.cerebras.ai/",
    "sambanova": "https://cloud.sambanova.ai/",
    "nvidia": "https://build.nvidia.com/",
    "mistral": "https://console.mistral.ai/",
    "fireworks": "https://fireworks.ai/account/api-keys",
    "cloudflare": "https://dash.cloudflare.com/",
    "deepseek": "https://platform.deepseek.com/",
    "google": "https://aistudio.google.com/app/apikey",
}


def _resolve_provider_settings(override: dict) -> tuple[str, str, str, str, str]:
    settings = get_settings()
    provider = str(override.get("provider") or settings.ai_provider).strip().lower()
    model = str(override.get("model") or "").strip()
    api_key = str(override.get("api_key") or "").strip()
    base_url = str(override.get("base_url") or "").strip()

    provider_key_map = {
        "openai": ("openai_api_key", "chat_model"),
        "codex": ("openai_api_key", "chat_model"),
        "anthropic": ("anthropic_api_key", "anthropic_chat_model"),
        "google": ("google_api_key", "google_chat_model"),
        "mistral": ("mistral_api_key", "mistral_chat_model"),
        "groq": ("groq_api_key", "groq_chat_model"),
        "openrouter": ("openrouter_api_key", "openrouter_chat_model"),
        "deepseek": ("deepseek_api_key", "deepseek_chat_model"),
        "fireworks": ("fireworks_api_key", "chat_model"),
        "nvidia": ("nvidia_api_key", "chat_model"),
        "cerebras": ("cerebras_api_key", "chat_model"),
    }

    if not api_key and provider in provider_key_map:
        key_attr, model_attr = provider_key_map[provider]
        api_key = getattr(settings, key_attr, "")
        if not model:
            model = getattr(settings, model_attr, "")

    return provider, model, api_key, base_url, settings.chat_model


def _get_openai_client(api_key: str, base_url: str = "") -> OpenAI:
    cache_key = f"{api_key}:{base_url}"
    if cache_key not in _client_cache:
        _client_cache[cache_key] = OpenAI(
            api_key=api_key or ("local-key" if base_url else ""),
            base_url=base_url or None,
            timeout=60.0,
            max_retries=1,
        )
    return _client_cache[cache_key]


def _anthropic_completion(messages: list[dict], model: str, api_key: str, temperature: float) -> str:
    system = "\n\n".join(item["content"] for item in messages if item.get("role") == "system")
    chat_messages = [
        {"role": item["role"], "content": item["content"]}
        for item in messages
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": model,
            "max_tokens": 8192,
            "temperature": temperature,
            "system": system,
            "messages": chat_messages,
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    parts = data.get("content", [])
    return "".join(part.get("text", "") for part in parts if part.get("type") == "text")


def _anthropic_stream(messages: list[dict], model: str, api_key: str, temperature: float) -> Generator[str, None, None]:
    system = "\n\n".join(item["content"] for item in messages if item.get("role") == "system")
    chat_messages = [
        {"role": item["role"], "content": item["content"]}
        for item in messages
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": model,
            "max_tokens": 8192,
            "temperature": temperature,
            "system": system,
            "messages": chat_messages,
            "stream": True,
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for line in response:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    if data.get("type") == "content_block_delta":
                        delta = data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield text
                except json.JSONDecodeError:
                    continue
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Anthropic streaming failed: {exc}") from exc


def _google_completion(messages: list[dict], model: str, api_key: str, temperature: float) -> str:
    contents = []
    system_instruction = ""
    for item in messages:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role == "system":
            system_instruction += content + "\n"
        elif role in {"user", "assistant"}:
            role_map = {"user": "user", "assistant": "model"}
            contents.append({"role": role_map.get(role, "user"), "parts": [{"text": content}]})

    body: dict = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
    }
    if system_instruction.strip():
        body["systemInstruction"] = {"parts": [{"text": system_instruction.strip()}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    return ""


def _google_stream(messages: list[dict], model: str, api_key: str, temperature: float) -> Generator[str, None, None]:
    contents = []
    system_instruction = ""
    for item in messages:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role == "system":
            system_instruction += content + "\n"
        elif role in {"user", "assistant"}:
            role_map = {"user": "user", "assistant": "model"}
            contents.append({"role": role_map.get(role, "user"), "parts": [{"text": content}]})

    body: dict = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
    }
    if system_instruction.strip():
        body["systemInstruction"] = {"parts": [{"text": system_instruction.strip()}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={api_key}&alt=sse"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            for line in response:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            text = part.get("text", "")
                            if text:
                                yield text
                except json.JSONDecodeError:
                    continue
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Google streaming failed: {exc}") from exc


def _openai_compatible_stream(provider: str, client: OpenAI, model: str, messages: list[dict],
                               temperature: float) -> Generator[str, None, None]:
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


OPENAI_COMPATIBLE_PROVIDERS = {
    "openai", "custom", "kimi", "codex", "openrouter", "groq", "mistral",
    "cerebras", "nvidia", "vercel", "ofox", "fireworks", "sambanova",
    "scaleway", "nebius", "novita", "hyperbolic", "inference", "cloudflare",
    "deepseek",
}


def chat_completion(
    messages: list[dict],
    temperature: float = 0.2,
    json_mode: bool = False,
    model_config: dict | None = None,
) -> str:
    provider, model, api_key, base_url, fallback_model = _resolve_provider_settings(model_config or {})

    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        if not api_key and provider not in {"custom"}:
            signup_url = FREE_PROVIDER_URLS.get(provider, "")
            hint = f"\n\nFree API key available: {signup_url}" if signup_url else ""
            raise RuntimeError(
                f"API key required for {provider.upper()}.{hint}\n\n"
                f"To use {provider}:\n"
                f"1. Go to {signup_url or 'the provider console'}\n"
                f"2. Sign up (free tier available)\n"
                f"3. Copy your API key\n"
                f"4. Open Settings > Models & API Keys > paste key\n\n"
                f"Or switch to Aurine Native (no key needed) in Model settings."
            )
        client = _get_openai_client(api_key, base_url)
        kwargs = {
            "model": model or fallback_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    if provider == "anthropic":
        if not api_key:
            raise RuntimeError(
                "API key required for Anthropic.\n\n"
                "To use Claude models:\n"
                "1. Go to https://console.anthropic.com/\n"
                "2. Sign up and create an API key\n"
                "3. Open Settings > Models & API Keys > paste key\n\n"
                "Or switch to Aurine Native (no key needed) in Model settings."
            )
        return _anthropic_completion(messages, model or "claude-sonnet-4-20250514", api_key, temperature)

    if provider == "google":
        if not api_key:
            raise RuntimeError(
                "API key required for Google Gemini.\n\n"
                "To use Gemini models:\n"
                "1. Go to https://aistudio.google.com/app/apikey\n"
                "2. Create a free API key\n"
                "3. Open Settings > Models & API Keys > paste key"
            )
        return _google_completion(messages, model or "gemini-2.0-flash", api_key, temperature)

    if provider == "aurine":
        reload_settings()
        if _ensure_ollama():
            payload = {
                "model": _native_model_name(model),
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if json_mode:
                payload["format"] = "json"
            try:
                response = _ollama_post("/api/chat", payload)
                return response.get("message", {}).get("content", "")
            except _AurineServerFallbackError:
                return _aurine_server_post(messages, temperature, stream=False, json_mode=json_mode).get("content", "")
            except Exception:
                pass

        if _aurine_server_running():
            return _aurine_server_post(messages, temperature, stream=False, json_mode=json_mode).get("content", "")

        raise RuntimeError(
            "Aurine AI is starting up...\n\n"
            "First time setup is automatic. Just ensure:\n"
            "1. Ollama is installed: https://ollama.com\n"
            "2. Ollama is running\n"
            "3. Restart Aurine\n\n"
            "The AI model will auto-download on first run (~4GB)."
        )

    if provider == "ollama":
        payload = {
            "model": model or "qwen2.5-coder:7b",
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            response = _ollama_post("/api/chat", payload)
            return response.get("message", {}).get("content", "")
        except _OllamaFallbackError as fb:
            return chat_completion(
                messages=messages, temperature=temperature,
                json_mode=json_mode, model_config=fb.config
            )

    raise RuntimeError(f"AI provider '{provider}' is not supported. Use aurine, ollama, openai, anthropic, google, groq, or custom.")


def chat_completion_stream(
    messages: list[dict],
    temperature: float = 0.2,
    model_config: dict | None = None,
) -> Generator[str, None, None]:
    provider, model, api_key, base_url, fallback_model = _resolve_provider_settings(model_config or {})

    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        if not api_key and provider not in {"custom"}:
            signup_url = FREE_PROVIDER_URLS.get(provider, "")
            hint = f"\n\nFree API key available: {signup_url}" if signup_url else ""
            raise RuntimeError(
                f"API key required for {provider.upper()}.{hint}\n\n"
                f"To use {provider}:\n"
                f"1. Go to {signup_url or 'the provider console'}\n"
                f"2. Sign up (free tier available)\n"
                f"3. Copy your API key\n"
                f"4. Open Settings > Models & API Keys > paste key\n\n"
                f"Or switch to Aurine Native (no key needed) in Model settings."
            )
        client = _get_openai_client(api_key, base_url)
        yield from _openai_compatible_stream(provider, client, model or fallback_model, messages, temperature)
        return

    if provider == "anthropic":
        if not api_key:
            raise RuntimeError(
                "API key required for Anthropic.\n\n"
                "To use Claude models:\n"
                "1. Go to https://console.anthropic.com/\n"
                "2. Sign up and create an API key\n"
                "3. Open Settings > Models & API Keys > paste key\n\n"
                "Or switch to Aurine Native (no key needed) in Model settings."
            )
        yield from _anthropic_stream(messages, model or "claude-sonnet-4-20250514", api_key, temperature)
        return

    if provider == "google":
        if not api_key:
            raise RuntimeError(
                "API key required for Google Gemini.\n\n"
                "To use Gemini models:\n"
                "1. Go to https://aistudio.google.com/app/apikey\n"
                "2. Create a free API key\n"
                "3. Open Settings > Models & API Keys > paste key"
            )
        yield from _google_stream(messages, model or "gemini-2.0-flash", api_key, temperature)
        return

    if provider == "aurine":
        reload_settings()
        if _ensure_ollama():
            payload = {
                "model": _native_model_name(model),
                "messages": messages,
                "stream": True,
                "options": {"temperature": temperature},
            }
            try:
                yield from _ollama_stream("/api/chat", payload)
                return
            except _AurineServerFallbackError:
                yield from _aurine_server_stream(messages, temperature)
                return
            except Exception:
                pass

        if _aurine_server_running():
            yield from _aurine_server_stream(messages, temperature)
            return

        raise RuntimeError(
            "Aurine AI is starting up...\n\n"
            "First time setup is automatic. Just ensure:\n"
            "1. Ollama is installed: https://ollama.com\n"
            "2. Ollama is running\n"
            "3. Restart Aurine\n\n"
            "The AI model will auto-download on first run (~4GB)."
        )

    if provider == "ollama":
        payload = {
            "model": model or "qwen2.5-coder:7b",
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        try:
            yield from _ollama_stream("/api/chat", payload)
            return
        except _OllamaFallbackError as fb:
            yield from chat_completion_stream(
                messages=messages, temperature=temperature, model_config=fb.config
            )
            return

    raise RuntimeError(f"AI provider '{provider}' is not supported. Use aurine, ollama, openai, anthropic, google, groq, or custom.")


def _aurine_server_stream(messages: list[dict], temperature: float) -> Generator[str, None, None]:
    result = _aurine_server_post(messages, temperature, stream=True)
    if isinstance(result, Generator):
        yield from result


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if _ollama_running():
        embeddings: list[list[float]] = []
        for text in texts:
            try:
                response = _ollama_post(
                    "/api/embeddings",
                    {"model": settings.aurine_embedding_model, "prompt": text},
                )
                embeddings.append(response.get("embedding", []))
            except Exception:
                break
        else:
            if embeddings and all(len(e) > 0 for e in embeddings):
                return embeddings

    if settings.openai_api_key:
        try:
            client = _get_openai_client(settings.openai_api_key)
            response = client.embeddings.create(
                model=settings.embedding_model or "text-embedding-3-small",
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception:
            pass

    if not _ollama_running():
        raise RuntimeError(
            "Embeddings require Ollama or an OpenAI-compatible API key.\n"
            "1. Install Ollama: https://ollama.com\n"
            "2. Start Ollama (nomic-embed-text will auto-download)"
        )

    embeddings = []
    for text in texts:
        response = _ollama_post(
            "/api/embeddings",
            {"model": settings.aurine_embedding_model, "prompt": text},
        )
        embeddings.append(response.get("embedding", []))
    return embeddings


# ---------------------------------------------------------------------------
# Agentic tool-calling loop
# ---------------------------------------------------------------------------

def _supports_tool_calls(provider: str) -> bool:
    return provider in {
        "openai", "codex", "anthropic", "groq", "openrouter",
        "mistral", "nvidia", "fireworks", "cerebras", "sambanova",
        "deepseek", "custom",
    }


def _parse_openai_tool_calls(response) -> list[dict]:
    if not hasattr(response, "choices") or not response.choices:
        return []
    msg = response.choices[0].message
    if not hasattr(msg, "tool_calls") or not msg.tool_calls:
        return []
    calls = []
    for tc in msg.tool_calls:
        fn = tc.function
        try:
            args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
        except (json.JSONDecodeError, TypeError):
            args = {}
        calls.append({"id": tc.id, "name": fn.name, "arguments": args})
    return calls


def _parse_anthropic_tool_calls(content_blocks: list) -> tuple[str, list[dict]]:
    text_parts = []
    tool_calls = []
    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id", ""),
                "name": block.get("name", ""),
                "arguments": block.get("input", {}),
            })
    return "\n".join(text_parts), tool_calls


def _extract_text_from_response(response) -> str:
    content = getattr(response, "choices", [{}])[0].message.content if hasattr(response, "choices") else ""
    return content or ""


def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_executor,
    temperature: float = 0.2,
    model_config: dict | None = None,
    max_iterations: int = 10,
) -> dict:
    provider, model, api_key, base_url, fallback_model = _resolve_provider_settings(model_config or {})

    all_tool_calls: list[dict] = []
    current_messages = list(messages)

    for iteration in range(max_iterations):
        if provider in OPENAI_COMPATIBLE_PROVIDERS:
            if not api_key and provider not in {"custom"}:
                answer = chat_completion(messages=current_messages, temperature=temperature, model_config=model_config)
                return {"answer": answer, "tool_calls": []}

            client = _get_openai_client(api_key, base_url)
            response = client.chat.completions.create(
                model=model or fallback_model,
                messages=current_messages,
                temperature=temperature,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
            )
            msg = response.choices[0].message
            text_content = msg.content or ""
            openai_calls = _parse_openai_tool_calls(response)

            if not openai_calls:
                return {"answer": text_content, "tool_calls": all_tool_calls}

            current_messages.append({
                "role": "assistant",
                "content": text_content or None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}}
                    for tc in openai_calls
                ],
            })

            for tc in openai_calls:
                result = tool_executor(tc["name"], tc["arguments"])
                all_tool_calls.append({"name": tc["name"], "arguments": tc["arguments"], "result": result[:2000]})
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result[:8000],
                })

        elif provider == "anthropic":
            key = api_key
            if not key:
                answer = chat_completion(messages=current_messages, temperature=temperature, model_config=model_config)
                return {"answer": answer, "tool_calls": []}

            system = "\n\n".join(item["content"] for item in current_messages if item.get("role") == "system")
            chat_messages = [
                {"role": item["role"], "content": item["content"]}
                for item in current_messages
                if item.get("role") in {"user", "assistant"} and item.get("content")
            ]
            ant_tools = [
                {"name": t["function"]["name"], "description": t["function"]["description"],
                 "input_schema": t["function"]["parameters"]}
                for t in tools
            ] if tools else []
            body = {
                "model": model or "claude-sonnet-4-20250514",
                "max_tokens": 8192,
                "temperature": temperature,
                "system": system,
                "messages": chat_messages,
            }
            if ant_tools:
                body["tools"] = ant_tools
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content_blocks = data.get("content", [])
            text_content, ant_calls = _parse_anthropic_tool_calls(content_blocks)

            if not ant_calls:
                return {"answer": text_content, "tool_calls": all_tool_calls}

            current_messages.append({"role": "assistant", "content": content_blocks})

            for tc in ant_calls:
                result = tool_executor(tc["name"], tc["arguments"])
                all_tool_calls.append({"name": tc["name"], "arguments": tc["arguments"], "result": result[:2000]})
                current_messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tc["id"], "content": result[:8000]}],
                })

        elif provider == "aurine":
            if not _ensure_ollama():
                if _aurine_server_running():
                    answer = chat_completion(messages=current_messages, temperature=temperature, model_config=model_config)
                    return {"answer": answer, "tool_calls": all_tool_calls}
                raise RuntimeError("Aurine requires Ollama. Install from https://ollama.com")

            ollama_model = _native_model_name(model)
            payload = {
                "model": ollama_model,
                "messages": current_messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if tools:
                ollama_tools = []
                for t in tools:
                    ollama_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                        },
                    })
                payload["tools"] = ollama_tools
            try:
                response = _ollama_post("/api/chat", payload)
            except _AurineServerFallbackError:
                answer = chat_completion(messages=current_messages, temperature=temperature, model_config=model_config)
                return {"answer": answer, "tool_calls": all_tool_calls}
            message = response.get("message", {})
            text_content = message.get("content", "")
            ollama_calls = message.get("tool_calls", [])

            if not ollama_calls:
                return {"answer": text_content, "tool_calls": all_tool_calls}

            current_messages.append({"role": "assistant", "content": text_content or None, "tool_calls": ollama_calls})

            for tc in ollama_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}")) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
                except (json.JSONDecodeError, TypeError):
                    args = {}
                result = tool_executor(name, args)
                all_tool_calls.append({"name": name, "arguments": args, "result": result[:2000]})
                current_messages.append({"role": "tool", "content": result[:8000]})

        elif provider == "ollama":
            ollama_model = model or "qwen2.5-coder:7b"
            payload = {
                "model": ollama_model,
                "messages": current_messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            if tools:
                ollama_tools = []
                for t in tools:
                    ollama_tools.append({
                        "type": "function",
                        "function": {
                            "name": t["function"]["name"],
                            "description": t["function"]["description"],
                            "parameters": t["function"]["parameters"],
                        },
                    })
                payload["tools"] = ollama_tools
            response = _ollama_post("/api/chat", payload)
            message = response.get("message", {})
            text_content = message.get("content", "")
            ollama_calls = message.get("tool_calls", [])

            if not ollama_calls:
                return {"answer": text_content, "tool_calls": all_tool_calls}

            current_messages.append({"role": "assistant", "content": text_content or None, "tool_calls": ollama_calls})

            for tc in ollama_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}")) if isinstance(fn.get("arguments"), str) else fn.get("arguments", {})
                except (json.JSONDecodeError, TypeError):
                    args = {}
                result = tool_executor(name, args)
                all_tool_calls.append({"name": name, "arguments": args, "result": result[:2000]})
                current_messages.append({"role": "tool", "content": result[:8000]})
        else:
            return {"answer": chat_completion(messages=current_messages, temperature=temperature, model_config=model_config), "tool_calls": []}

    final_text = ""
    if current_messages and current_messages[-1].get("role") == "assistant":
        final_text = current_messages[-1].get("content", "") or ""
    if not final_text:
        final_text = "I completed the requested operations." if all_tool_calls else "I was unable to complete the request."
    return {"answer": final_text, "tool_calls": all_tool_calls}


def supports_tools(model_config: dict | None = None) -> bool:
    settings = get_settings()
    if not model_config:
        return False
    provider = str(model_config.get("provider") or settings.ai_provider).strip().lower()
    model = str(model_config.get("model", "")).lower()
    if provider in OPENAI_COMPATIBLE_PROVIDERS | {"anthropic"}:
        return True
    if provider in {"aurine", "ollama"}:
        return "qwen" in model or "llama" in model or "mistral" in model or "deepseek" in model or "codestral" in model
    return False
