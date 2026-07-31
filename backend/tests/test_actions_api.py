from fastapi.testclient import TestClient
from fastapi import FastAPI


def _test_app() -> FastAPI:
    from backend.app.api.actions import router

    app = FastAPI()
    app.include_router(router, prefix="/api/actions")
    return app


def test_action_center_api_forwards_filters(monkeypatch):
    from backend.app.api import actions as actions_api

    monkeypatch.setenv("HOME_AGENT_API_KEY", "test-action-center-key")
    captured: dict[str, object] = {}

    def fake_build_action_center(reference_time, *, mode, limit, include_external):
        captured.update({
            "reference_time": reference_time,
            "mode": mode,
            "limit": limit,
            "include_external": include_external,
        })
        return {
            "generated_at": "2030-01-10T12:00:00+00:00",
            "timezone": "UTC",
            "mode": mode,
            "summary": {"total": 0, "returned": 0, "critical": 0, "high": 0, "overdue": 0, "due_today": 0, "requires_approval": 0, "reminders_due": 0},
            "actions": [],
        }

    monkeypatch.setattr(actions_api, "build_action_center", fake_build_action_center)
    client = TestClient(_test_app())

    response = client.get(
        "/api/actions?mode=all&limit=7&include_external=true&reference_time=2030-01-10T12:00:00Z",
        headers={"X-API-Key": "test-action-center-key"},
    )

    assert response.status_code == 200
    assert captured["mode"] == "all"
    assert captured["limit"] == 7
    assert captured["include_external"] is True
    assert captured["reference_time"].isoformat() == "2030-01-10T12:00:00+00:00"


def test_action_center_api_rejects_unknown_mode(monkeypatch):
    response = TestClient(_test_app()).get(
        "/api/actions?mode=urgent",
    )

    assert response.status_code == 422
