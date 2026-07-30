import httpx
import pytest

import backend.app.agent.llm as llm


class _Response:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FailThenSucceedClient:
    def __init__(self, payload):
        self.calls = []
        self.payload = payload

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs.get("json", {})))
        if len(self.calls) <= 2:
            raise httpx.ConnectError("model unavailable")
        return _Response(self.payload)


@pytest.fixture(autouse=True)
def reset_llm_state(monkeypatch):
    monkeypatch.setattr(llm, "_circuit_consecutive_errors", 0)
    monkeypatch.setattr(llm, "_circuit_cooldown_until", 0.0)
    monkeypatch.setattr(llm, "_backoff", _no_backoff)
    monkeypatch.setattr(llm, "_log_error", lambda *args: None)
    monkeypatch.setattr(llm, "_log_call", lambda *args: None)


async def _no_backoff(_seconds):
    return None


@pytest.mark.asyncio
async def test_openai_compatible_fallback_uses_fallback_model(monkeypatch):
    client = _FailThenSucceedClient({
        "choices": [{"message": {"role": "assistant", "content": "fallback ok"}}]
    })
    monkeypatch.setattr(llm, "get_http_client", lambda: client)
    monkeypatch.setattr(llm, "OPENAI_MODEL", "primary-model")
    monkeypatch.setattr(llm, "LLM_FALLBACK_MODEL", "fallback-model")

    result = await llm._chat_openai(
        [{"role": "user", "content": "hello"}], None, None, "primary-model"
    )

    assert result["model"] == "fallback-model"
    assert result["message"]["content"] == "fallback ok"
    assert client.calls[-1][1]["model"] == "fallback-model"
    assert len(client.calls) == 3


@pytest.mark.asyncio
async def test_ollama_fallback_uses_fallback_model(monkeypatch):
    client = _FailThenSucceedClient({
        "message": {"role": "assistant", "content": "fallback ok"}
    })
    monkeypatch.setattr(llm, "get_http_client", lambda: client)
    monkeypatch.setattr(llm, "OLLAMA_MODEL", "primary-model")
    monkeypatch.setattr(llm, "LLM_FALLBACK_MODEL", "fallback-model")

    result = await llm._chat_ollama(
        [{"role": "user", "content": "hello"}], None, None, "primary-model"
    )

    assert result["model"] == "fallback-model"
    assert result["message"]["content"] == "fallback ok"
    assert client.calls[-1][1]["model"] == "fallback-model"
    assert len(client.calls) == 3
