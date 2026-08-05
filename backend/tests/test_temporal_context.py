from datetime import datetime, timezone

import pytest

from backend.app.storage import db
from backend.app.temporal.time_context import build_temporal_context, classify_due, classify_due_date


def test_temporal_context_uses_one_local_day_boundary():
    reference = datetime(2030, 1, 1, 23, 30, tzinfo=timezone.utc)
    berlin = build_temporal_context(reference, "Europe/Berlin")
    utc = build_temporal_context(reference, "UTC")

    assert berlin.today.isoformat() == "2030-01-02"
    assert utc.today.isoformat() == "2030-01-01"
    assert classify_due("2030-01-02T01:15:00+01:00", berlin, 0).status == "due_today"
    assert classify_due("2030-01-02T01:15:00+01:00", utc, 0).status == "planned"


def test_temporal_context_interprets_naive_calendar_time_in_user_zone():
    context = build_temporal_context(
        datetime(2030, 1, 1, 23, 30, tzinfo=timezone.utc),
        "Europe/Berlin",
    )

    parsed = context.parse("2030-01-02T00:45:00", assume_local=True)

    assert parsed == datetime(2030, 1, 1, 23, 45, tzinfo=timezone.utc)


def test_date_only_signals_use_local_day_boundaries():
    context = build_temporal_context(
        datetime(2030, 1, 1, 23, 30, tzinfo=timezone.utc),
        "Europe/Berlin",
    )

    assert context.today.isoformat() == "2030-01-02"
    assert classify_due_date("2030-01-02", context, 7).status == "due_today"
    assert classify_due_date("2030-01-09", context, 7).status == "upcoming"
    assert classify_due_date("2030-01-01", context, 7).status == "overdue"


def test_temporal_context_rejects_naive_reference_time():
    with pytest.raises(ValueError, match="timezone"):
        build_temporal_context(datetime(2030, 1, 1, 12, 0))


def test_countdowns_use_injected_temporal_context(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "real")
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "temporal.db"))
    db.init_db()

    from backend.app.countdown.countdown_service import add_countdown, get_all_countdowns

    add_countdown("Завтра", "2030-01-02")
    context = build_temporal_context(datetime(2030, 1, 1, 23, 30, tzinfo=timezone.utc), "Europe/Berlin")

    result = get_all_countdowns(temporal_context=context)

    assert result["countdowns"][0]["days_remaining"] == 0
