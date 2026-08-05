from datetime import datetime, timezone

import pytest

from backend.app.storage import db


@pytest.fixture
def notification_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "notifications.db"))
    db.init_db()


@pytest.mark.asyncio
async def test_delivery_coalesces_and_marks_domain_reminders(notification_db, monkeypatch):
    from backend.app.commitments.commitment_service import create_commitment, get_due_reminders, transition_commitment
    from backend.app.notifications import delivery_service
    from backend.app.subscriptions.subscription_service import create_subscription, get_due_reminders as get_subscription_reminders, transition_subscription

    commitment = create_commitment(
        "Позвонить в страховую",
        source_type="CHAT",
        deadline_at="2030-01-20T10:00:00+00:00",
        reminder_at="2030-01-10T10:00:00+00:00",
    )
    transition_commitment(commitment["id"], "approve")
    subscription = create_subscription(
        "Example Pro",
        subscription_type="TRIAL",
        trial_ends_at="2030-01-20T10:00:00+00:00",
        reminder_at="2030-01-10T10:00:00+00:00",
        source_type="EMAIL",
    )
    transition_subscription(subscription["id"], "approve")
    sent: list[str] = []

    async def fake_send(message: str, chat_id: str | None = None):
        sent.append(message)
        return True

    monkeypatch.setattr(delivery_service, "send_notification", fake_send)
    now = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)
    result = await delivery_service.deliver_action_notifications(now)

    assert result["status"] == "sent"
    assert result["coalesced"] is True
    assert len(result["action_ids"]) == 2
    assert len(sent) == 1
    assert "страховую" in sent[0]
    assert get_due_reminders("2030-01-11T00:00:00+00:00") == []
    assert get_subscription_reminders("2030-01-11T00:00:00+00:00") == []

    second = await delivery_service.deliver_action_notifications(now)
    assert second["status"] == "idle"


@pytest.mark.asyncio
async def test_delivery_respects_quiet_hours_for_noncritical_actions(notification_db, monkeypatch):
    from backend.app.commitments.commitment_service import create_commitment
    from backend.app.notifications import delivery_service

    create_commitment("Проверить предложение", source_type="EMAIL")
    sent: list[str] = []

    async def fake_send(message: str, chat_id: str | None = None):
        sent.append(message)
        return True

    monkeypatch.setattr(delivery_service, "send_notification", fake_send)
    result = await delivery_service.deliver_action_notifications(
        datetime(2030, 1, 10, 23, 0, tzinfo=timezone.utc)
    )

    assert result["status"] == "suppressed"
    assert result["reason"] == "quiet_hours"
    assert sent == []


@pytest.mark.asyncio
async def test_calendar_delivery_only_dedupes_events_actually_sent(notification_db, monkeypatch):
    from backend.app.calendar import calendar_service
    from backend.app.notifications import delivery_service

    delivery_service.update_notification_preferences(max_messages_per_window=1)
    events = [
        {
            "uid": "event-1",
            "summary": "Первое событие",
            "start": "2030-01-10T12:05:00+00:00",
            "reminder_minutes": 5,
        },
        {
            "uid": "event-2",
            "summary": "Второе событие",
            "start": "2030-01-10T12:10:00+00:00",
            "reminder_minutes": 10,
        },
    ]
    sent: list[str] = []

    def fake_list_events(start_date: str, end_date: str):
        return events

    async def fake_send(message: str, chat_id: str | None = None):
        sent.append(message)
        return True

    monkeypatch.setattr(calendar_service, "list_events", fake_list_events)
    monkeypatch.setattr(delivery_service, "send_notification", fake_send)
    now = datetime(2030, 1, 10, 12, 0, tzinfo=timezone.utc)

    first = await delivery_service.deliver_calendar_reminders(now)
    second = await delivery_service.deliver_calendar_reminders(now)

    assert first == {"status": "sent", "event_ids": ["event-1"]}
    assert second == {"status": "sent", "event_ids": ["event-2"]}
    assert len(sent) == 2
    assert "Первое событие" in sent[0]
    assert "Второе событие" not in sent[0]
    assert "Второе событие" in sent[1]


@pytest.mark.asyncio
async def test_calendar_delivery_uses_coalesce_window(notification_db, monkeypatch):
    from backend.app.calendar import calendar_service
    from backend.app.notifications import delivery_service

    delivery_service.update_notification_preferences(coalesce_window_minutes=15)
    sent: list[str] = []

    def fake_list_events(start_date: str, end_date: str):
        return [{
            "uid": "old-event",
            "summary": "Старое событие",
            "start": "2030-01-10T11:44:00+00:00",
            "reminder_minutes": 0,
        }]

    async def fake_send(message: str, chat_id: str | None = None):
        sent.append(message)
        return True

    monkeypatch.setattr(calendar_service, "list_events", fake_list_events)
    monkeypatch.setattr(delivery_service, "send_notification", fake_send)

    result = await delivery_service.deliver_calendar_reminders(
        datetime(2030, 1, 10, 12, 0, tzinfo=timezone.utc)
    )

    assert result == {"status": "idle", "reason": "nothing_new", "event_ids": []}
    assert sent == []
