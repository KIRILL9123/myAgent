import pytest

from backend.app.storage import db
from backend.app.subscriptions.subscription_service import (
    create_subscription,
    get_due_reminders,
    get_subscription_events,
    list_subscriptions_by_source_prefix,
    mark_reminder_sent,
    transition_subscription,
)
import backend.app.subscriptions.email_extractor as email_extractor


@pytest.fixture
def subscription_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "subscriptions.db"))
    db.init_db()


def test_subscription_lifecycle_and_reminder(subscription_db):
    subscription = create_subscription(
        name="Example Pro",
        provider="Example",
        subscription_type="TRIAL",
        amount=9.99,
        currency="EUR",
        trial_ends_at="2030-01-10T12:00:00+00:00",
        next_charge_at="2030-01-10T12:00:00+00:00",
        reminder_at="2030-01-03T12:00:00+00:00",
        cancellation_url="javascript:alert(1)",
        source_type="MANUAL",
    )
    assert subscription["status"] == "PROPOSED"
    assert subscription["cancellation_url"] is None

    active = transition_subscription(subscription["id"], "approve", {"channel": "web"})
    assert active["status"] == "ACTIVE"
    assert get_due_reminders("2030-01-04T00:00:00+00:00")[0]["id"] == subscription["id"]

    mark_reminder_sent(subscription["id"], "2030-01-04T01:00:00+00:00")
    assert get_due_reminders("2030-01-05T00:00:00+00:00") == []

    cancelled = transition_subscription(subscription["id"], "cancel")
    assert cancelled["status"] == "CANCELLED"
    assert [event["event_type"] for event in get_subscription_events(subscription["id"])] == [
        "CREATED", "APPROVE", "REMINDER_SENT", "CANCEL",
    ]


@pytest.mark.asyncio
async def test_email_subscription_extraction_is_approval_gated_and_idempotent(subscription_db, monkeypatch):
    async def fake_chat(*args, **kwargs):
        return {"message": {"content": "{" \
            "\"subscriptions\": [{" \
            "\"name\": \"Video Pro\", \"provider\": \"Video\", " \
            "\"subscription_type\": \"TRIAL\", \"amount\": 12.99, " \
            "\"currency\": \"EUR\", \"trial_ends_at\": " \
            "\"2030-02-10T12:00:00+00:00\", \"confidence\": 0.91}]" \
            "}"}}

    monkeypatch.setattr(email_extractor, "chat", fake_chat)
    kwargs = {
        "account": "gmail",
        "sender": "billing@example.com",
        "recipient": "user@example.com",
        "subject": "Your free trial ends soon",
        "date": "Thu, 01 Feb 2030 12:00:00 +0000",
        "preview": "Your trial ends on 10 February 2030 and then costs 12.99 EUR.",
    }
    first = await email_extractor.extract_email_subscriptions(**kwargs)
    second = await email_extractor.extract_email_subscriptions(**kwargs)

    assert len(first) == 1
    assert first[0]["status"] == "PROPOSED"
    assert second[0]["id"] == first[0]["id"]
    assert first[0]["source_type"] == "EMAIL"
    assert list_subscriptions_by_source_prefix(first[0]["source_ref"].rsplit(":", 1)[0])
