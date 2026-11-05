from datetime import datetime, timezone

import pytest

from backend.app.storage import db


@pytest.fixture
def integration_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "integration.db"))
    monkeypatch.setenv("EXECUTION_MODE", "real")
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    db.init_db()


@pytest.mark.asyncio
async def test_tool_registry_domains_action_center_and_notification_dry_run(
    integration_db, monkeypatch
):
    from backend.app.action_center_service import build_action_center
    from backend.app.agent.tool_registry import dispatch_tool
    from backend.app.calendar.calendar_service import list_events
    from backend.app.finance.finance_service import get_transactions
    from backend.app.notifications import delivery_service

    reference_time = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)
    task_result = dispatch_tool(
        "create_task",
        {
            "title": "Проверить страховку",
            "deadline_at": "2030-01-11T12:00:00+00:00",
            "reminder_at": "2030-01-10T11:30:00+00:00",
        },
    )
    assert task_result["status"] == "created"
    task_id = task_result["task"]["id"]

    event_result = dispatch_tool(
        "create_event",
        {
            "title": "Встреча со страховой",
            "start_datetime": "2030-01-11T10:00:00+00:00",
            "end_datetime": "2030-01-11T10:30:00+00:00",
            "commitment_id": task_id,
            "allow_conflicts": True,
        },
    )
    assert event_result["status"] == "created"
    assert event_result["uid"]

    transaction_result = dispatch_tool(
        "add_transaction",
        {
            "type": "expense",
            "amount": 20,
            "category": "Еда",
            "description": "Тестовый smoke-сценарий",
            "date": "2030-01-10",
            "currency": "EUR",
        },
    )
    assert transaction_result["status"] == "success"

    events = list_events("2030-01-11T00:00:00+00:00", "2030-01-12T00:00:00+00:00")
    assert [event["uid"] for event in events] == [event_result["uid"]]

    transactions = get_transactions("2030-01-10", "2030-01-10")
    assert [(item["amount"], item["category"], item["currency"]) for item in transactions] == [
        (20.0, "Еда", "EUR")
    ]

    center = build_action_center(
        reference_time,
        mode="attention",
        include_external=False,
    )
    commitment_actions = [
        item for item in center["actions"] if item["kind"] == "commitment"
    ]
    assert [item["source_id"] for item in commitment_actions] == [task_id]
    assert commitment_actions[0]["reminder_due"] is True

    async def fake_send(message: str, chat_id: str | None = None):
        return {
            "status": "dry_run",
            "would_do": {"action": "send_notification", "message": message},
        }

    monkeypatch.setattr(delivery_service, "send_notification", fake_send)
    delivery = await delivery_service.deliver_action_notifications(reference_time)

    assert delivery["status"] == "dry_run"
    assert delivery["action_ids"] == [f"commitment:{task_id}"]
    assert "Проверить страховку" in delivery["message"]
