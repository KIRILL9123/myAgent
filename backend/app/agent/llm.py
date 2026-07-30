import httpx
import os
import json
import time
import asyncio
from typing import Any
from dotenv import load_dotenv

load_dotenv()

# ─── Provider configuration (env-driven, no hardcoding) ──────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

OPENAI_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
OPENAI_API_KEY = os.getenv("LLM_API_KEY", "local")
OPENAI_MODEL = os.getenv("LLM_MODEL", "Ternary-Bonsai-27B-Q2_0")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "3000"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "")

LLM_ROLE_MAIN = os.getenv("LLM_ROLE_MAIN", OPENAI_MODEL if LLM_PROVIDER == "openai_compatible" else OLLAMA_MODEL)
LLM_ROLE_EXTRACTOR = os.getenv("LLM_ROLE_EXTRACTOR", OLLAMA_MODEL)
LLM_ROLE_CLASSIFIER = os.getenv("LLM_ROLE_CLASSIFIER", OLLAMA_MODEL)


def get_model_for_role(role: str) -> str:
    if role == "extractor":
        return LLM_ROLE_EXTRACTOR
    if role == "classifier":
        return LLM_ROLE_CLASSIFIER
    return LLM_ROLE_MAIN

_http_client: httpx.AsyncClient | None = None

_circuit_consecutive_errors = 0
_circuit_cooldown_until = 0.0
ERROR_THRESHOLD = 3
COOLDOWN_SECONDS = 30

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=LLM_TIMEOUT)
    return _http_client

async def close_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()

def _current_model() -> str:
    return OPENAI_MODEL if LLM_PROVIDER == "openai_compatible" else OLLAMA_MODEL

def _in_cooldown() -> bool:
    global _circuit_consecutive_errors, _circuit_cooldown_until
    if _circuit_consecutive_errors < ERROR_THRESHOLD:
        return False
    if time.monotonic() < _circuit_cooldown_until:
        return True
    _circuit_consecutive_errors = ERROR_THRESHOLD - 1
    return False

def _record_error():
    global _circuit_consecutive_errors, _circuit_cooldown_until
    _circuit_consecutive_errors += 1
    if _circuit_consecutive_errors >= ERROR_THRESHOLD:
        _circuit_cooldown_until = time.monotonic() + COOLDOWN_SECONDS

def _record_success():
    global _circuit_consecutive_errors
    _circuit_consecutive_errors = 0

async def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_format: str | None = None,
) -> dict[str, Any]:
    if _in_cooldown():
        return {"status": "error",
                "message": "LLM backend is temporarily offline (cooldown after repeated errors). "
                           "It will be retried automatically."}
    if LLM_PROVIDER == "openai_compatible":
        return await _chat_openai(messages, tools, response_format)
    return await _chat_ollama(messages, tools, response_format)

async def _chat_ollama(messages, tools, response_format) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": LLM_TEMPERATURE},
    }
    if response_format:
        payload["format"] = response_format
    if tools:
        payload["tools"] = tools
        payload["options"]["parallel_tool_calls"] = False
        payload["parallel_tool_calls"] = False

    last_err: Exception | None = None
    client = get_http_client()
    for attempt in range(2):
        try:
            t0 = time.monotonic()
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            latency = time.monotonic() - t0
            resp.raise_for_status()
            data = resp.json()
            _log_call("ollama", OLLAMA_MODEL, resp.status_code, latency,
                      bool(data.get("message", {}).get("tool_calls")))
            _record_success()
            return {"model": OLLAMA_MODEL, "message": data.get("message", {})}
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_err = e
            if attempt == 0:
                await _backoff(attempt + 1)
            continue
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            _log_call("ollama", OLLAMA_MODEL, status, 0, False)
            if status in (429, 500, 502, 503, 504):
                return {"status": "error",
                        "message": "Локальная модель (Ollama) временно перегружена. Попробуйте позже."}
            return {"status": "error",
                    "message": f"Ollama rejected the request (HTTP {status})."}
        except Exception as e:
            _log_error("ollama", OLLAMA_MODEL, e)
            _record_error()
            return {"status": "error",
                    "message": f"Failed to communicate with Ollama: {type(e).__name__}"}

    _log_error("ollama", OLLAMA_MODEL, last_err)
    _record_error()
    if LLM_FALLBACK_MODEL:
        print(f"[LLM] falling back to {LLM_FALLBACK_MODEL}")
        payload["model"] = LLM_FALLBACK_MODEL
        try:
            t0 = time.monotonic()
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            _log_call("ollama", LLM_FALLBACK_MODEL, resp.status_code, time.monotonic() - t0,
                      bool(data.get("message", {}).get("tool_calls")))
            _record_success()
            return {"model": LLM_FALLBACK_MODEL, "message": data.get("message", {})}
        except Exception as fb_err:
            _log_error("ollama", LLM_FALLBACK_MODEL, fb_err)
    return {"status": "error",
            "message": f"Failed to communicate with Ollama. Is it running?"}

async def _chat_openai(messages, tools, response_format) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if response_format == "json":
        payload["response_format"] = {"type": "json_object"}
        if not any(m.get("role") == "user" for m in messages):
            messages.append({"role": "user", "content": "Обработай запрос выше."})

    last_err: Exception | None = None
    client = get_http_client()
    for attempt in range(2):
        try:
            t0 = time.monotonic()
            resp = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            )
            latency = time.monotonic() - t0
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""
            tool_calls = _normalize_tool_calls(msg.get("tool_calls"))
            msg["content"] = content
            msg["tool_calls"] = tool_calls
            _log_call("openai_compatible", OPENAI_MODEL, resp.status_code, latency, bool(tool_calls))
            _record_success()
            return {"model": OPENAI_MODEL, "message": msg}
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_err = e
            if attempt == 0:
                await _backoff(attempt + 1)
            continue
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            _log_call("openai_compatible", OPENAI_MODEL, status, 0, False)
            if status in (429, 500, 502, 503, 504):
                return {"status": "error",
                        "message": "Локальная модель временно перегружена. "
                                   "Пожалуйста, попробуйте ещё раз через несколько секунд."}
            return {"status": "error",
                    "message": f"LLM server rejected the request (HTTP {status})."}
        except Exception as e:
            _log_error("openai_compatible", OPENAI_MODEL, e)
            _record_error()
            return {"status": "error",
                    "message": f"Failed to communicate with OpenAI-compatible server: {type(e).__name__}"}

    _log_error("openai_compatible", OPENAI_MODEL, last_err)
    _record_error()
    if LLM_FALLBACK_MODEL:
        print(f"[LLM] falling back to {LLM_FALLBACK_MODEL}")
        payload["model"] = LLM_FALLBACK_MODEL
        try:
            t0 = time.monotonic()
            resp = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            msg["content"] = msg.get("content") or ""
            msg["tool_calls"] = _normalize_tool_calls(msg.get("tool_calls"))
            _log_call("openai_compatible", LLM_FALLBACK_MODEL, resp.status_code, time.monotonic() - t0, bool(msg["tool_calls"]))
            _record_success()
            return {"model": LLM_FALLBACK_MODEL, "message": msg}
        except Exception as fb_err:
            _log_error("openai_compatible", LLM_FALLBACK_MODEL, fb_err)
    return {"status": "error",
            "message": f"Bonsai/OpenAI server not reachable. "
                       f"Start it via C:\\AI\\start-bonsai.ps1"}

def _normalize_tool_calls(raw_calls) -> list[dict[str, Any]]:
    if not raw_calls:
        return []
    out = []
    for tc in raw_calls:
        func = tc.get("function", {})
        args = func.get("arguments", {})
        if isinstance(args, str):
            if not args.strip():
                args = {}
            else:
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    pass
        out.append({
            "id": tc.get("id"),
            "type": tc.get("type", "function"),
            "function": {"name": func.get("name"), "arguments": args},
        })
    return out

async def _backoff(attempt: int):
    await asyncio.sleep(min(2.0 ** attempt, 2.0))

def _log_call(provider: str, model: str, status: int, latency: float, has_tools: bool):
    print(f"[LLM] provider={provider} model={model} status={status} "
          f"latency={latency:.2f}s tools={has_tools}")

def _log_error(provider: str, model: str, err: Any):
    print(f"[LLM] ERROR provider={provider} model={model} type={type(err).__name__}")
