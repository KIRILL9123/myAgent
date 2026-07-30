import pytest

from backend.app.commitments.commitment_service import (
    create_commitment,
    expire_overdue,
    get_commitment_events,
    list_commitments,
    transition_commitment,
    update_commitment,
)
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
