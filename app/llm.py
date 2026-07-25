import json
import logging
import urllib.request
import urllib.error
from typing import Generator

from .config import get_settings

logger = logging.getLogger("aurine.llm")


def _build_providers(settings):
    providers = []
    provider = settings.ai_provider.lower() if settings.ai_provider else ""

    if provider in ("aurine", "ollama"):
        ollama_url = settings.ollama_base_url
        if provider == "aurine":
            providers.append(("aurine", lambda msgs, temp: _ollama(msgs, settings.aurine_native_model, ollama_url, temp)))
        else:
            providers.append(("ollama", lambda msgs, temp: _ollama(msgs, settings.ollama_chat_model, ollama_url, temp)))
        if settings.google_api_key:
            providers.append(("google", lambda msgs, temp: _google(msgs, settings.google_chat_model, settings.google_api_key, temp)))
        if settings.groq_api_key:
            providers.append(("groq", lambda msgs, temp: _openai(msgs, settings.groq_chat_model, settings.groq_api_key, temp, False, "https://api.groq.com/openai/v1")))
        if settings.deepseek_api_key:
            providers.append(("deepseek", lambda msgs, temp: _openai(msgs, settings.deepseek_chat_model, settings.deepseek_api_key, temp, False, "https://api.deepseek.com")))
        if settings.openai_api_key:
            providers.append(("openai", lambda msgs, temp: _openai(msgs, settings.openai_chat_model, settings.openai_api_key, temp, False)))
        if settings.anthropic_api_key:
            providers.append(("anthropic", lambda msgs, temp: _anthropic(msgs, settings.anthropic_chat_model, settings.anthropic_api_key, temp)))
    else:
        if settings.google_api_key:
            providers.append(("google", lambda msgs, temp: _google(msgs, settings.google_chat_model, settings.google_api_key, temp)))
        if settings.groq_api_key:
            providers.append(("groq", lambda msgs, temp: _openai(msgs, settings.groq_chat_model, settings.groq_api_key, temp, False, "https://api.groq.com/openai/v1")))
        if settings.deepseek_api_key:
            providers.append(("deepseek", lambda msgs, temp: _openai(msgs, settings.deepseek_chat_model, settings.deepseek_api_key, temp, False, "https://api.deepseek.com")))
        if settings.openai_api_key:
            providers.append(("openai", lambda msgs, temp: _openai(msgs, settings.openai_chat_model, settings.openai_api_key, temp, False)))
        if settings.anthropic_api_key:
            providers.append(("anthropic", lambda msgs, temp: _anthropic(msgs, settings.anthropic_chat_model, settings.anthropic_api_key, temp)))
        if settings.ollama_base_url:
            if provider == "ollama":
                providers.append(("ollama", lambda msgs, temp: _ollama(msgs, settings.ollama_chat_model, settings.ollama_base_url, temp)))
            else:
                providers.append(("ollama", lambda msgs, temp: _ollama(msgs, settings.aurine_native_model, settings.ollama_base_url, temp)))

    return providers


def _call_with_fallback(providers, preferred_provider, messages, temperature, json_mode=False):
    if not providers:
        return (
            "No AI provider configured.\n\n"
            "Options:\n"
            "  1. Local (free, no key needed): Install Ollama + pull model\n"
            "     ollama pull qwen2.5-coder:7b\n"
            "  2. Cloud (free keys available):\n"
            "     - GOOGLE_API_KEY: https://aistudio.google.com/app/apikey\n"
            "     - GROQ_API_KEY: https://console.groq.com/keys\n"
            "     - DEEPSEEK_API_KEY: https://platform.deepseek.com/\n\n"
            "Use /connect to set up."
        )

    ordered = []
    preferred_name = preferred_provider.lower() if preferred_provider else ""
    for name, fn in providers:
        if name == preferred_name:
            ordered.insert(0, (name, fn))
        else:
            ordered.append((name, fn))

    last_error = None
    for name, fn in ordered:
        try:
            result = fn(messages, temperature)
            if result and not str(result).startswith("Error:") and not str(result).startswith("No AI provider"):
                return result
            last_error = f"Provider '{name}' returned empty response."
            continue
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            if e.code == 429:
                logger.warning(f"Provider '{name}' quota/rate limit hit (429). Trying next...")
                last_error = f"Provider '{name}' quota exceeded. "
                continue
            elif e.code in (401, 403):
                logger.warning(f"Provider '{name}' auth error ({e.code}). Trying next...")
                last_error = f"Provider '{name}' API key invalid. "
                continue
            elif e.code == 402:
                logger.warning(f"Provider '{name}' payment required (402). Trying next...")
                last_error = f"Provider '{name}' requires payment. "
                continue
            last_error = f"Provider '{name}' HTTP {e.code}: {error_body[:200]}"
            logger.warning(last_error)
            continue
        except urllib.error.URLError as e:
            last_error = f"Provider '{name}' connection failed: {e.reason}"
            logger.warning(last_error)
            continue
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "insufficient_quota" in err_str.lower():
                logger.warning(f"Provider '{name}' quota exceeded. Trying next...")
                last_error = f"Provider '{name}' quota exceeded. "
                continue
            if "401" in err_str or "403" in err_str or "invalid" in err_str.lower():
                logger.warning(f"Provider '{name}' auth error. Trying next...")
                last_error = f"Provider '{name}' API key invalid. "
                continue
            last_error = f"Provider '{name}' error: {err_str[:200]}"
            logger.warning(last_error)
            continue

    if last_error:
        return (
            f"All AI providers failed.\n{last_error}\n\n"
            "Fix:\n"
            "  Local: ollama pull qwen2.5-coder:7b\n"
            "  Cloud: /connect to set up Google Gemini, Groq, or DeepSeek (free)"
        )
    return "All AI providers failed. Use /connect to set up a working provider."


def chat_completion(
    messages,
    temperature=0.2,
    json_mode=False,
    model_config=None,
):
    settings = get_settings()
    provider = settings.ai_provider.lower()
    providers = _build_providers(settings)

    if model_config:
        mc_provider = model_config.get("provider", "").lower() if isinstance(model_config, dict) else ""
        mc_model = model_config.get("model", "") if isinstance(model_config, dict) else ""
        if mc_provider in ("aurine", "ollama") and mc_model:
            ollama_url = settings.ollama_base_url
            return _ollama(messages, mc_model, ollama_url, temperature)

    return _call_with_fallback(providers, provider, messages, temperature, json_mode)


def _ollama(messages, model, base_url, temperature):
    ollama_msgs = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role in ("system", "user", "assistant") and content:
            ollama_msgs.append({"role": role, "content": content})

    if not ollama_msgs:
        return "No valid messages to send."

    payload = {
        "model": model,
        "messages": ollama_msgs,
        "stream": False,
        "options": {"temperature": temperature},
    }

    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise Exception(
            f"Ollama not running at {base_url}. "
            f"Start it: ollama serve\nError: {e.reason}"
        )
    except Exception as e:
        raise Exception(f"Ollama error: {e}")

    return data.get("message", {}).get("content", "")


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

    if not contents:
        return "No valid messages to send."

    body = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": 8192}}
    if sys.strip():
        body["systemInstruction"] = {"parts": [{"text": sys.strip()}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        if e.code == 429:
            raise Exception(f"Google Gemini quota/rate limit exceeded (429). {error_body[:200]}")
        elif e.code in (401, 403):
            raise Exception(f"Google Gemini API key invalid ({e.code}). {error_body[:200]}")
        raise Exception(f"Google Gemini error {e.code}: {error_body[:300]}")
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text:
        finish = data.get("candidates", [{}])[0].get("finishReason", "")
        if finish == "SAFETY":
            return "Response blocked by safety filters. Try rephrasing your message."
        return "No response from Google Gemini. Try again."
    return text


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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        if e.code == 429:
            raise Exception(f"API rate limit/quota exceeded (429). {error_body[:200]}")
        elif e.code in (401, 403):
            raise Exception(f"API key invalid ({e.code}). {error_body[:200]}")
        elif e.code == 402:
            raise Exception(f"Payment required ({e.code}). {error_body[:200]}")
        raise Exception(f"API error {e.code}: {error_body[:300]}")
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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        if e.code == 429:
            raise Exception(f"Anthropic rate limit/quota exceeded (429). {error_body[:200]}")
        elif e.code in (401, 403):
            raise Exception(f"Anthropic API key invalid ({e.code}). {error_body[:200]}")
        raise Exception(f"Anthropic error {e.code}: {error_body[:300]}")
    return "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text")


def chat_completion_stream(messages, temperature=0.2, model_config=None):
    result = chat_completion(messages, temperature, model_config=model_config)
    yield result


def chat_with_tools(messages, tools, tool_executor=None, temperature=0.2, model_config=None, max_iterations=5):
    settings = get_settings()
    provider = settings.ai_provider.lower()
    providers = _build_providers(settings)

    if model_config and isinstance(model_config, dict):
        mc_provider = model_config.get("provider", "").lower()
        if mc_provider in ("aurine", "ollama"):
            mc_model = model_config.get("model", "")
            if mc_model:
                ordered = [("local", lambda msgs, temp: _ollama(msgs, mc_model, settings.ollama_base_url, temp))]
                for name, fn in providers:
                    if name not in ("aurine", "ollama"):
                        ordered.append((name, fn))
                providers = ordered

    tool_desc = ""
    for t in tools:
        func = t.get("function", t)
        tool_desc += f"- {func.get('name', '')}: {func.get('description', '')}\n"

    enhanced = list(messages)
    tool_system = (
        "\n\nYou have tools available. To use a tool, respond with ONLY valid JSON (no extra text):\n"
        '{"message": "brief explanation of what you are doing", "actions": [{"tool": "tool_name", "param1": "value1"}]}\n'
        "If no tool is needed, respond with:\n"
        '{"message": "your answer here", "actions": []}\n'
        f"\nAvailable tools:\n{tool_desc}"
    )
    if enhanced and enhanced[0].get("role") == "system":
        enhanced[0] = {"role": "system", "content": enhanced[0]["content"] + tool_system}
    else:
        enhanced.insert(0, {"role": "system", "content": f"You are an AI assistant with tools.{tool_system}"})

    tool_calls = []

    for iteration in range(max_iterations):
        content = _call_with_fallback(providers, provider, enhanced, temperature, json_mode=True)

        parsed = None
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            try:
                import re
                match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
            except Exception:
                pass

        if not parsed or not isinstance(parsed, dict):
            return {"answer": content, "tool_calls": tool_calls}

        message = parsed.get("message", "")
        actions = parsed.get("actions", [])

        if not actions or not tool_executor:
            return {"answer": message or content, "tool_calls": tool_calls}

        tool_results_text = ""
        for action in actions:
            tool_name = action.get("tool", "")
            params = {k: v for k, v in action.items() if k != "tool"}
            try:
                result = tool_executor(tool_name, params)
            except Exception as e:
                result = f"Tool error: {e}"
            tool_calls.append({"tool": tool_name, "arguments": params, "result": str(result)[:2000]})
            tool_results_text += f"\nTool '{tool_name}' result:\n{str(result)[:2000]}\n"

        enhanced.append({"role": "assistant", "content": content})
        enhanced.append({"role": "user", "content": f"Tool results:\n{tool_results_text}\nNow provide your final answer as JSON: {{\"message\": \"your answer\", \"actions\": []}}"})

    final = _call_with_fallback(providers, provider, enhanced, temperature, json_mode=True)
    try:
        final_parsed = json.loads(final)
        return {"answer": final_parsed.get("message", final), "tool_calls": tool_calls}
    except Exception:
        return {"answer": final, "tool_calls": tool_calls}


def supports_tools(model_config=None):
    return True
