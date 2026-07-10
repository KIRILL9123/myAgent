import httpx
import os
import json
from typing import Any

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    """Returns a shared, persistent httpx.AsyncClient to enable connection pooling."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=60.0)
    return _http_client

async def close_http_client():
    """Closes the shared httpx.AsyncClient during application shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()

async def chat_with_ollama(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_format: str | None = None
) -> dict[str, Any]:
    """
    Sends a chat request to the local Ollama instance.
    Reuses a global HTTP client for connection pooling.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    
    if response_format:
        payload["format"] = response_format
    
    if tools:
        payload["tools"] = tools
        # Disable parallel tool calls as requested
        payload["options"]["parallel_tool_calls"] = False
        # Also add it to the root in case Ollama supports it there
        payload["parallel_tool_calls"] = False

    client = get_http_client()
    try:
        response = await client.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": "error", "message": f"Failed to communicate with Ollama: {str(e)}"}
