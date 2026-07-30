import pytest

from backend.app.commitments.commitment_service import (
    create_commitment,
    commitments_for_calendar_events,
    expire_overdue,
    get_due_reminders,
    get_commitment_events,
    list_commitments,
    transition_commitment,
    link_calendar_event,
    mark_reminder_sent,
    unlink_calendar_event,
    update_commitment,
)
import backend.app.commitments.email_extractor as email_extractor
from backend.app.storage import db


@pytest.fixture
def commitment_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "commitments.db"))
    db.init_db()


def test_commitment_lifecycle_preserves_approval_provenance(commitment_db):
    commitment = create_commitment(
        title="Send the project proposal",
        source_type="CHAT",
        source_ref="conversation-42",
        deadline_at="2030-01-10T12:00:00+00:00",
        reminder_at="2030-01-09T12:00:00+00:00",
        confidence=0.8,
        provenance={"message_id": "message-7"},
    )

    assert commitment["status"] == "PROPOSED"
    assert commitment["provenance"] == {"message_id": "message-7"}

    active = transition_commitment(
        commitment["id"], "approve", {"approved_by": "user", "channel": "web"}
    )
    assert active["status"] == "ACTIVE"
    assert active["approval_provenance"] == {"approved_by": "user", "channel": "web"}

    completed = transition_commitment(commitment["id"], "complete")
    assert completed["status"] == "COMPLETED"
    assert [event["event_type"] for event in get_commitment_events(commitment["id"])] == [
        "CREATED", "APPROVE", "COMPLETE"
    ]


def test_expire_overdue_only_expires_active_commitments(commitment_db):
    overdue = create_commitment(
        title="Overdue task", source_type="EMAIL", deadline_at="2020-01-01T00:00:00+00:00"
    )
    transition_commitment(overdue["id"], "approve")
    proposed = create_commitment(
        title="Future proposal", source_type="DOCUMENT", deadline_at="2020-01-01T00:00:00+00:00"
    )

    expired = expire_overdue("2026-07-30T00:00:00+00:00")

    assert [item["id"] for item in expired] == [overdue["id"]]
    assert expired[0]["status"] == "EXPIRED"
    assert list_commitments(status="PROPOSED")[0]["id"] == proposed["id"]


def test_commitment_validation_and_editing(commitment_db):
    with pytest.raises(ValueError, match="source_type"):
        create_commitment("Bad source", source_type="UNKNOWN")

    commitment = create_commitment("Initial title", source_type="CALENDAR")
    updated = update_commitment(commitment["id"], title="Updated title", owner="Alex")
    assert updated["title"] == "Updated title"
    assert updated["owner"] == "Alex"

    transition_commitment(commitment["id"], "approve")
    transition_commitment(commitment["id"], "complete")
    with pytest.raises(ValueError, match="terminal"):
        update_commitment(commitment["id"], title="Should not change")


def test_calendar_links_are_explicit_and_do_not_complete_commitment(commitment_db):
    commitment = create_commitment("Prepare presentation", source_type="CALENDAR")

    linked = link_calendar_event(
        commitment["id"], "calendar-event-1", "2030-01-10T10:00:00+00:00"
    )
    assert linked["status"] == "PROPOSED"
    assert linked["related_calendar_event_ids"] == ["calendar-event-1"]
    assert linked["deadline_at"] == "2030-01-10T10:00:00+00:00"

    grouped = commitments_for_calendar_events(["calendar-event-1", "missing-event"])
    assert grouped["calendar-event-1"][0]["id"] == commitment["id"]
    assert "missing-event" not in grouped

    unlinked = unlink_calendar_event(commitment["id"], "calendar-event-1")
    assert unlinked["related_calendar_event_ids"] == []
    assert [event["event_type"] for event in get_commitment_events(commitment["id"])] == [
        "CREATED", "CALENDAR_LINKED", "CALENDAR_UNLINKED"
    ]


@pytest.mark.asyncio
async def test_email_extraction_creates_proposals_and_is_idempotent(commitment_db, monkeypatch):
    async def fake_chat(*args, **kwargs):
        return {
            "message": {"content": '{"commitments": [{"title": "Cancel the trial before renewal", "owner": "user", "deadline_at": "2030-01-10T12:00:00+00:00", "confidence": 0.9}]}'},
        }

    monkeypatch.setattr(email_extractor, "chat", fake_chat)
    email = {
        "account": "gmail",
        "sender": "billing@example.com",
        "recipient": "me@example.com",
        "subject": "Your trial ends soon",
        "date": "2030-01-01T12:00:00+00:00",
        "preview": "Cancel before renewal to avoid a charge.",
    }

    first = await email_extractor.extract_email_commitments(**email)
    second = await email_extractor.extract_email_commitments(**email)

    assert len(first) == 1
    assert first[0]["status"] == "PROPOSED"
    assert first[0]["source_type"] == "EMAIL"
    assert [item["id"] for item in second] == [first[0]["id"]]


def test_due_reminder_is_selected_once_and_recorded(commitment_db):
    commitment = create_commitment(
        "Cancel trial", source_type="EMAIL",
        deadline_at="2030-01-10T12:00:00+00:00",
        reminder_at="2030-01-01T12:00:00+00:00",
    )
    transition_commitment(commitment["id"], "approve")

    due = get_due_reminders("2030-01-02T12:00:00+00:00")
    assert [item["id"] for item in due] == [commitment["id"]]

    mark_reminder_sent(commitment["id"], "2030-01-02T12:01:00+00:00")
    assert get_due_reminders("2030-01-03T12:00:00+00:00") == []
