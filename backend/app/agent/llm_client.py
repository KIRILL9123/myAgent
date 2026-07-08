import httpx
import os
import json
from typing import Any

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

async def chat_with_ollama(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_format: str | None = None
) -> dict[str, Any]:
    """
    Sends a chat request to the local Ollama instance.
    Supports basic tool calling if provided.
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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to communicate with Ollama: {str(e)}"}
