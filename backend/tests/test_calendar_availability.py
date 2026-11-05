from datetime import datetime, timezone

import pytest

from backend.app.calendar import availability_service
from backend.app.temporal.time_context import build_temporal_context


def _context():
    return build_temporal_context(
        datetime(2026, 8, 4, 8, 0, tzinfo=timezone.utc),
        "Europe/Berlin",
    )


def test_finds_slots_after_busy_event_without_writing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        availability_service,
        "list_events",
        lambda start, end: calls.append((start, end)) or [
            {
                "uid": "busy-1",
                "summary": "Busy",
                "start": "2026-08-05T09:00:00+02:00",
                "end": "2026-08-05T11:00:00+02:00",
            }
        ],
    )
    monkeypatch.setattr(availability_service, "extract_calendar_preferences", lambda: [])

    result = availability_service.find_calendar_slots(
        "2026-08-05",
        "2026-08-05",
        duration_minutes=60,
        earliest_time="09:00",
        latest_time="13:00",
        max_results=2,
        temporal_context=_context(),
    )

    assert result["status"] == "ok"
    assert [slot["start"] for slot in result["slots"]] == [
        "2026-08-05T11:00:00+02:00",
        "2026-08-05T12:00:00+02:00",
    ]
    assert result["events_checked"] == 1
    assert len(calls) == 1


def test_applies_approved_memory_window_and_blocked_weekday(monkeypatch):
    monkeypatch.setattr(availability_service, "list_events", lambda start, end: [])
    monkeypatch.setattr(
        availability_service,
        "extract_calendar_preferences",
        lambda: [
            {"kind": "earliest_start", "value": "10:30"},
            {"kind": "blocked_weekday", "value": 2},  # Wednesday
        ],
    )

    blocked = availability_service.find_calendar_slots(
        "2026-08-05",
        "2026-08-05",
        duration_minutes=60,
        earliest_time="09:00",
        latest_time="13:00",
        temporal_context=_context(),
    )
    available = availability_service.find_calendar_slots(
        "2026-08-06",
        "2026-08-06",
        duration_minutes=60,
        earliest_time="09:00",
        latest_time="13:00",
        max_results=1,
        temporal_context=_context(),
    )

    assert blocked["status"] == "no_slots"
    assert blocked["effective_window"]["blocked_weekdays"] == [2]
    assert available["slots"][0]["start"] == "2026-08-06T10:30:00+02:00"


def test_allows_a_31_day_inclusive_range(monkeypatch):
    monkeypatch.setattr(availability_service, "list_events", lambda start, end: [])
    monkeypatch.setattr(availability_service, "extract_calendar_preferences", lambda: [])

    result = availability_service.find_calendar_slots(
        "2026-08-04",
        "2026-09-03",
        max_results=1,
        temporal_context=_context(),
    )

    assert result["status"] == "ok"
    assert result["start_date"] == "2026-08-04"
    assert result["end_date"] == "2026-09-03"


def test_rejects_ranges_longer_than_31_days(monkeypatch):
    with pytest.raises(ValueError, match="no longer than 31"):
        availability_service.find_calendar_slots(
            "2026-08-04",
            "2026-09-04",
            temporal_context=_context(),
        )


def test_rejects_invalid_max_results(monkeypatch):
    with pytest.raises(ValueError, match="max_results"):
        availability_service.find_calendar_slots(
            "2026-08-05",
            "2026-08-05",
            max_results=21,
            temporal_context=_context(),
        )
