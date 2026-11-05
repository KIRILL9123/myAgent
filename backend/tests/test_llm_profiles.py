import httpx
import pytest

import backend.app.agent.llm as llm


class _Response:
    status_code = 200

    def __init__(self, payload=None):
        self._payload = payload or {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def __init__(self):
        self.posts = []
        self.gets = []

    async def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return _Response()

    async def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return _Response()


@pytest.fixture(autouse=True)
def reset_provider_state(monkeypatch):
    monkeypatch.setattr(llm, "_active_provider", "local")
    monkeypatch.setattr(llm, "_model_overrides", {})
    monkeypatch.setattr(llm, "DEEPSEEK_API_KEY", "test-secret")
    monkeypatch.setattr(llm, "_log_call", lambda *args: None)
    monkeypatch.setattr(llm, "_log_error", lambda *args: None)
    monkeypatch.setattr(llm, "_record_success", lambda: None)


def test_provider_status_never_exposes_api_key():
    status = llm.get_provider_status()
    assert status["active_provider"] == "local"
    assert "test-secret" not in repr(status)
    deepseek = next(item for item in status["profiles"] if item["id"] == "deepseek")
    assert deepseek["configured"] is True


def test_provider_can_switch_and_override_role_models():
    llm.set_provider_models("deepseek", {"main": "deepseek-v4-flash-custom"})
    status = llm.set_active_provider("deepseek")
    assert status["active_provider"] == "deepseek"
    assert llm.get_model_for_role("main") == "deepseek-v4-flash-custom"


def test_deepseek_redaction_removes_pii_and_sensitive_fields():
    messages, context = llm.redact_messages_for_remote([
        {"role": "user", "content": "Напиши на user@example.com, телефон +49 170 1234567"},
        {"role": "tool", "content": '{"body":"Секретное письмо", "id": "commitment-42"}'},
    ])
    serialized = repr(messages)
    assert "user@example.com" not in serialized
    assert "+49 170 1234567" not in serialized
    assert "Секретное письмо" not in serialized
    assert "commitment-42" in serialized
    assert context.restore(messages[0]["content"]).startswith("Напиши на user@example.com")


@pytest.mark.asyncio
async def test_deepseek_chat_uses_api_endpoint_and_redacts_payload(monkeypatch):
    client = _Client()
    monkeypatch.setattr(llm, "get_http_client", lambda: client)
    monkeypatch.setattr(llm, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    profile = llm._profiles()["deepseek"]
    result = await llm._chat_openai([
        {"role": "user", "content": "Проверь user@example.com"},
    ], None, None, "deepseek-v4-flash", profile)

    assert result["message"]["content"] == "ok"
    url, kwargs = client.posts[0]
    assert url == "https://api.deepseek.com/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer test-secret"
    assert "user@example.com" not in repr(kwargs["json"])


@pytest.mark.asyncio
async def test_provider_health_check_uses_authorization_without_returning_key(monkeypatch):
    client = _Client()
    monkeypatch.setattr(llm, "get_http_client", lambda: client)
    result = await llm.check_provider("deepseek")
    assert result["status"] == "ok"
    assert client.gets[0][0] == "https://api.deepseek.com/v1/models"
    assert client.gets[0][1]["headers"]["Authorization"] == "Bearer test-secret"
    assert "test-secret" not in repr(result)
