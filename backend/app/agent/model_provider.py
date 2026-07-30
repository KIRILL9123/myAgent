from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "3000"))


class ModelProvider(ABC):
    """Provider-neutral interface for chat model calls."""

    def __init__(self, client: httpx.AsyncClient, model: str, api_key: str = "local"):
        self.client = client
        self.model = model
        self.api_key = api_key

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class OllamaProvider(ModelProvider):
    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str):
        super().__init__(client, model)
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages, tools=None, response_format=None):
        payload: dict[str, Any] = {
            "model": self.model,
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

        response = await self.client.post(
            f"{self.base_url}/api/chat", json=payload, timeout=180.0
        )
        response.raise_for_status()
        return response.json()


class OpenAICompatibleProvider(ModelProvider):
    def __init__(self, client: httpx.AsyncClient, base_url: str, model: str, api_key: str):
        super().__init__(client, model, api_key)
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages, tools=None, response_format=None):
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_TOKENS,
        }
        if tools:
            payload["tools"] = tools
            payload["parallel_tool_calls"] = False
        if response_format:
            # OpenAI-compatible APIs use json_object rather than Ollama's
            # shorthand `json` response format.
            payload["response_format"] = {
                "type": "json_object" if response_format == "json" else response_format
            }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=180.0,
        )
        response.raise_for_status()
        data = response.json()
        choice = data.get("choices", [{}])[0]
        return {"message": choice.get("message", {})}
