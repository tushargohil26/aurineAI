import json
import urllib.request
import urllib.error
from typing import Generator

from .config import get_settings


def chat_completion(
    messages: list[dict],
    temperature: float = 0.2,
    json_mode: bool = False,
    model_config: dict | None = None,
) -> str:
    settings = get_settings()
    provider = settings.ai_provider.lower()

    if provider == "google" and settings.google_api_key:
        return _google_completion(messages, settings.google_chat_model, settings.google_api_key, temperature)

    if provider == "openai" and settings.openai_api_key:
        return _openai_completion(messages, settings.chat_model, settings.openai_api_key, temperature, json_mode)

    if provider == "groq" and settings.groq_api_key:
        return _openai_completion(messages, settings.groq_chat_model, settings.groq_api_key, temperature, json_mode,
                                  base_url="https://api.groq.com/openai/v1")

    if provider == "deepseek" and settings.deepseek_api_key:
        return _openai_completion(messages, settings.deepseek_chat_model, settings.deepseek_api_key, temperature, json_mode,
                                  base_url="https://api.deepseek.com")

    if provider == "anthropic" and settings.anthropic_api_key:
        return _anthropic_completion(messages, settings.anthropic_chat_model, settings.anthropic_api_key, temperature)

    if settings.google_api_key:
        return _google_completion(messages, settings.google_chat_model, settings.google_api_key, temperature)

    if settings.openai_api_key:
        return _openai_completion(messages, settings.chat_model, settings.openai_api_key, temperature, json_mode)

    return "No AI provider configured. Set GOOGLE_API_KEY or OPENAI_API_KEY in .env"


def _google_completion(messages: list[dict], model: str, api_key: str, temperature: float) -> str:
    contents = []
    system_instruction = ""
    for item in messages:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role == "system":
            system_instruction += content + "\n"
        elif role in ("user", "assistant"):
            role_map = {"user": "user", "assistant": "model"}
            contents.append({"role": role_map.get(role, "user"), "parts": [{"text": content}]})

    body = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192},
    }
    if system_instruction.strip():
        body["systemInstruction"] = {"parts": [{"text": system_instruction.strip()}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    return ""


def _openai_completion(messages: list[dict], model: str, api_key: str, temperature: float,
                       json_mode: bool = False, base_url: str = "https://api.openai.com/v1") -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return ""


def _anthropic_completion(messages: list[dict], model: str, api_key: str, temperature: float) -> str:
    system = "\n\n".join(item["content"] for item in messages if item.get("role") == "system")
    chat_messages = [
        {"role": item["role"], "content": item["content"]}
        for item in messages
        if item.get("role") in ("user", "assistant") and item.get("content")
    ]
    body = {
        "model": model,
        "max_tokens": 8192,
        "temperature": temperature,
        "system": system,
        "messages": chat_messages,
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    parts = data.get("content", [])
    return "".join(part.get("text", "") for part in parts if part.get("type") == "text")


def chat_completion_stream(
    messages: list[dict],
    temperature: float = 0.2,
    model_config: dict | None = None,
) -> Generator[str, None, None]:
    result = chat_completion(messages, temperature, model_config=model_config)
    yield result
