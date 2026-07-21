import json
import urllib.request
import urllib.error
from typing import Generator

from .config import get_settings


def chat_completion(
    messages,
    temperature=0.2,
    json_mode=False,
    model_config=None,
):
    settings = get_settings()
    provider = settings.ai_provider.lower()

    if provider == "google" and settings.google_api_key:
        return _google(messages, settings.google_chat_model, settings.google_api_key, temperature)

    if provider == "openai" and settings.openai_api_key:
        return _openai(messages, settings.openai_chat_model, settings.openai_api_key, temperature, json_mode)

    if provider == "groq" and settings.groq_api_key:
        return _openai(messages, settings.groq_chat_model, settings.groq_api_key, temperature, json_mode,
                       "https://api.groq.com/openai/v1")

    if provider == "deepseek" and settings.deepseek_api_key:
        return _openai(messages, settings.deepseek_chat_model, settings.deepseek_api_key, temperature, json_mode,
                       "https://api.deepseek.com")

    if provider == "anthropic" and settings.anthropic_api_key:
        return _anthropic(messages, settings.anthropic_chat_model, settings.anthropic_api_key, temperature)

    if settings.google_api_key:
        return _google(messages, settings.google_chat_model, settings.google_api_key, temperature)
    if settings.openai_api_key:
        return _openai(messages, settings.openai_chat_model, settings.openai_api_key, temperature, json_mode)

    return "No AI provider. Add GOOGLE_API_KEY to .env"


def _google(messages, model, api_key, temperature):
    contents = []
    sys = ""
    for m in messages:
        r = m.get("role", "user")
        c = m.get("content", "")
        if r == "system":
            sys += c + "\n"
        elif r in ("user", "assistant"):
            contents.append({"role": "user" if r == "user" else "model", "parts": [{"text": c}]})

    body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192}}
    if sys.strip():
        body["systemInstruction"] = {"parts": [{"text": sys.strip()}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _openai(messages, model, api_key, temperature, json_mode=False, base_url="https://api.openai.com/v1"):
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def _anthropic(messages, model, api_key, temperature):
    sys = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    chat = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") in ("user", "assistant") and m.get("content")]
    body = {"model": model, "max_tokens": 8192, "temperature": temperature, "system": sys, "messages": chat}
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text")


def chat_completion_stream(messages, temperature=0.2, model_config=None):
    yield chat_completion(messages, temperature, model_config=model_config)
