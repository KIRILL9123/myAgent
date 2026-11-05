from datetime import datetime, timezone

from backend.app.conflicts.conflict_service import detect_conflicts
from backend.app.temporal.time_context import build_temporal_context


def test_detects_commitment_deadline_inside_calendar_event():
    context = build_temporal_context(
        datetime(2026, 8, 4, 8, 0, tzinfo=timezone.utc),
        "Europe/Berlin",
    )
    result = detect_conflicts(
        temporal_context=context,
        events=[{
            "uid": "event-1",
            "summary": "DHL Termin",
            "start": "2026-08-04T10:00:00+02:00",
            "end": "2026-08-04T13:30:00+02:00",
        }],
        commitments=[{
            "id": "commitment-1",
            "title": "DHL Erste Tag",
            "status": "ACTIVE",
            "deadline_at": "2026-08-04T11:00:00+02:00",
            "related_calendar_event_ids": [],
        }],
    )

    assert result["status"] == "ok"
    assert [item["type"] for item in result["conflicts"]] == ["event_commitment"]
    assert result["conflicts"][0]["commitment_id"] == "commitment-1"


def test_detects_overlapping_events_and_respects_explicit_link():
    context = build_temporal_context(
        datetime(2026, 8, 4, 8, 0, tzinfo=timezone.utc),
        "Europe/Berlin",
    )
    events = [
        {"uid": "event-1", "summary": "Arbeit", "start": "2026-08-04T10:00:00+02:00", "end": "2026-08-04T12:00:00+02:00"},
        {"uid": "event-2", "summary": "Arzt", "start": "2026-08-04T11:00:00+02:00", "end": "2026-08-04T13:00:00+02:00"},
    ]
    result = detect_conflicts(
        temporal_context=context,
        events=events,
        commitments=[{
            "id": "commitment-1",
            "title": "Подготовиться",
            "status": "ACTIVE",
            "deadline_at": "2026-08-04T11:30:00+02:00",
            "related_calendar_event_ids": ["event-1"],
        }],
    )

    assert {item["type"] for item in result["conflicts"]} == {"event_overlap", "event_commitment"}
    commitment_conflict = next(item for item in result["conflicts"] if item["type"] == "event_commitment")
    overlap_conflict = next(item for item in result["conflicts"] if item["type"] == "event_overlap")
    assert commitment_conflict["event_uid"] == "event-2"
    assert overlap_conflict["related_event_uid"] == "event-2"
