import pytest
from datetime import datetime, timedelta, timezone

from backend.app.commitments.commitment_service import create_commitment, transition_commitment
from backend.app.state.state_service import (
    build_state_report,
    build_state_snapshot,
    get_state_history,
    persist_daily_snapshot,
)
from backend.app.storage import db
from backend.app.subscriptions.subscription_service import create_subscription, transition_subscription


@pytest.fixture
def state_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "state.db"))
    db.init_db()


def test_state_snapshot_prioritizes_overdue_signals(state_db):
    commitment = create_commitment(
        "Send overdue report",
        source_type="CHAT",
        deadline_at="2030-01-01T10:00:00+00:00",
    )
    transition_commitment(commitment["id"], "approve")
    subscription = create_subscription(
        "Video trial",
        subscription_type="TRIAL",
        trial_ends_at="2030-01-05T10:00:00+00:00",
        source_type="EMAIL",
    )
    transition_subscription(subscription["id"], "approve")

    snapshot = build_state_snapshot(
        reference_time=datetime(2030, 1, 3, 12, tzinfo=timezone.utc),
        include_external=False,
    )

    assert snapshot["health"] == "attention"
    assert snapshot["counts"]["active_commitments"] == 1
    assert snapshot["counts"]["active_subscriptions"] == 1
    assert snapshot["alerts"][0]["type"] == "commitment"
    assert snapshot["domains"]["calendar"]["status"] == "not_requested"


def test_state_snapshot_surfaces_pending_approvals(state_db):
    create_commitment("Review suggested task", source_type="EMAIL")
    create_subscription("Suggested trial", source_type="EMAIL")

    snapshot = build_state_snapshot(include_external=False)

    assert snapshot["counts"]["proposed_commitments"] == 1
    assert snapshot["counts"]["proposed_subscriptions"] == 1
    assert any(alert["type"] == "approval" for alert in snapshot["alerts"])


def test_state_reference_time_requires_timezone(state_db):
    from datetime import datetime

    with pytest.raises(ValueError, match="timezone"):
        build_state_snapshot(datetime(2030, 1, 1))


def test_state_history_upserts_one_daily_snapshot(state_db):
    snapshot = build_state_snapshot(include_external=False)
    persist_daily_snapshot(snapshot)
    first = get_state_history()
    persist_daily_snapshot({**snapshot, "headline": "Updated headline"})
    second = get_state_history()

    assert len(first) == 1
    assert len(second) == 1
    assert second[0]["headline"] == "Updated headline"


def test_state_report_contains_state_of_me(state_db):
    yesterday = build_state_snapshot(include_external=False)
    yesterday["generated_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    persist_daily_snapshot(yesterday)
    report = build_state_report(include_external=False)

    assert "state_of_me" in report
    assert report["state_of_me"]["has_previous_snapshot"] is True
