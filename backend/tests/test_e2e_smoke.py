import json
import os
import urllib.error
import urllib.request

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E") != "1",
    reason="Set RUN_E2E=1 to run against the live backend and model server",
)


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
MODEL_URL = os.getenv("E2E_MODEL_URL", "http://127.0.0.1:8080")


def request_json(url, payload=None):
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("HOME_AGENT_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read())


def test_live_model_and_chat_tool_confirmation_flow():
    models = request_json(f"{MODEL_URL}/v1/models")
    assert models["data"] or models["models"]

    health = request_json(f"{BASE_URL}/health")
    assert health["status"] == "ok"

    session_id = "pytest-e2e-smoke"
    basic = request_json(
        f"{BASE_URL}/api/chat",
        {"message": "Reply with exactly READY", "session_id": session_id},
    )
    assert basic["response"]

    tool = request_json(
        f"{BASE_URL}/api/chat",
        {"message": "Show my current countdowns", "session_id": session_id},
    )
    assert "get_all_countdowns" in tool["tool_calls"]

    red = request_json(
        f"{BASE_URL}/api/chat",
        {
            "message": "Send an email to test@example.com with subject E2E and body Do not send",
            "session_id": session_id,
        },
    )
    assert red["requires_confirmation"] is True
    assert "send_email" in red["tool_calls"]

    cancelled = request_json(
        f"{BASE_URL}/api/chat",
        {"message": "нет", "session_id": session_id},
    )
    assert "отменено" in cancelled["response"].lower()

    history = request_json(f"{BASE_URL}/api/history/{session_id}")
    assert len(history["history"]) >= 4
