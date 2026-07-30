import httpx
import os
import json
from typing import Any
from dotenv import load_dotenv
from backend.app.agent.model_provider import (
    ModelProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
)

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "local")
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:30b-a3b"))

_http_client: httpx.AsyncClient | None = None
_provider: ModelProvider | None = None

def get_http_client() -> httpx.AsyncClient:
    """Returns a shared, persistent httpx.AsyncClient to enable connection pooling."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=180.0)
    return _http_client

async def close_http_client():
    """Closes the shared httpx.AsyncClient during application shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    global _provider
    _provider = None


def get_model_provider() -> ModelProvider:
    global _provider
    if _provider is None:
        client = get_http_client()
        if LLM_PROVIDER == "openai_compatible":
            _provider = OpenAICompatibleProvider(
                client, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY
            )
        else:
            _provider = OllamaProvider(client, LLM_BASE_URL, LLM_MODEL)
    return _provider

async def chat_with_ollama(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_format: str | None = None
) -> dict[str, Any]:
    """
    Sends a chat request to the local Ollama instance.
    Reuses a global HTTP client for connection pooling.
    """
    try:
        return await get_model_provider().chat(messages, tools, response_format)
    except Exception as e:
        return {"status": "error", "message": f"Failed to communicate with model provider: {str(e)}"}
