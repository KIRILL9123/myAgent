from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from backend.app.api.calendar import EventCreate, EventUpdate, api_create_event, api_modify_event
from backend.app.calendar.local_calendar import list_events
from backend.app.conflicts.conflict_service import detect_conflicts, preview_event_conflicts
from backend.app.conflicts.preference_conflict_service import extract_calendar_preferences
from backend.app.memory.memory_service import save_extracted_fact
from backend.app.storage import db
from backend.app.temporal.time_context import build_temporal_context


def _context():
    return build_temporal_context(
        datetime(2026, 8, 4, 8, 0, tzinfo=timezone.utc),
        "Europe/Berlin",
    )


def _future_event_window() -> tuple[str, str, str]:
    local_now = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Berlin"))
    start = (local_now + timedelta(days=2)).replace(hour=9, minute=30, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    return (
        start.replace(tzinfo=None).isoformat(timespec="minutes"),
        end.replace(tzinfo=None).isoformat(timespec="minutes"),
        start.date().isoformat(),
    )


def test_extracts_only_explicit_rules_from_approved_preferences():
    rules = extract_calendar_preferences([
        {"id": 1, "category": "preference", "status": "approved", "content": "Не планировать встречи до 10:00."},
        {"id": 2, "category": "preference", "status": "pending_approval", "content": "Не планировать после 18:00."},
        {"id": 3, "category": "note", "status": "approved", "content": "Не планировать после 09:00."},
    ])

    assert [(item["kind"], item["value"], item["fact_id"]) for item in rules] == [
        ("earliest_start", "10:00", 1),
    ]


def test_detects_time_and_weekday_preference_conflicts():
    result = detect_conflicts(
        temporal_context=_context(),
        events=[
            {"uid": "early", "summary": "Ранняя встреча", "start": "2026-08-05T09:30:00+02:00", "end": "2026-08-05T10:30:00+02:00"},
            {"uid": "sunday", "summary": "Воскресное событие", "start": "2026-08-09T12:00:00+02:00", "end": "2026-08-09T13:00:00+02:00"},
        ],
        commitments=[],
        preference_facts=[
            {"id": 10, "category": "preference", "status": "approved", "content": "Не планировать встречи до 10:00."},
            {"id": 11, "category": "habit", "status": "approved", "content": "По воскресеньям не работаю."},
        ],
    )

    assert {item["event_uid"] for item in result["conflicts"]} == {"early", "sunday"}
    assert {item["preference_rule"]["kind"] for item in result["conflicts"]} == {"earliest_start", "blocked_weekday"}
    assert result["preferences_checked"] == 2


def test_exact_time_boundaries_are_allowed():
    result = detect_conflicts(
        temporal_context=_context(),
        events=[
            {"uid": "boundary", "summary": "Граница", "start": "2026-08-05T10:00:00+02:00", "end": "2026-08-05T18:00:00+02:00"},
        ],
        commitments=[],
        preference_facts=[
            {"id": 20, "category": "preference", "status": "approved", "content": "Не планировать встречи до 10:00 и не позже 18:00."},
        ],
    )

    assert result["conflicts"] == []


def test_preview_is_read_only_and_uses_approved_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "preview.db"))
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    db.init_db()
    fact_id, status = save_extracted_fact("Не планировать встречи до 10:00.", "preference", 0.99)
    assert status == "approved"
    start_datetime, end_datetime, event_date = _future_event_window()

    conflicts = preview_event_conflicts(
        title="Ранняя встреча",
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        timezone_name="Europe/Berlin",
    )

    assert conflicts[0]["type"] == "event_preference"
    assert conflicts[0]["fact_id"] == fact_id
    assert conflicts[0]["event_uid"] == "draft-event"
    assert list_events(f"{event_date}T00:00:00", f"{event_date}T23:59:59") == []


@pytest.mark.asyncio
async def test_calendar_api_requires_explicit_save_anyway(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "api-preview.db"))
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    db.init_db()
    save_extracted_fact("Не планировать встречи до 10:00.", "preference", 0.99)
    start_datetime, end_datetime, _ = _future_event_window()

    with pytest.raises(HTTPException) as error:
        await api_create_event(EventCreate(
            title="Ранняя встреча",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        ))
    assert error.value.status_code == 409
    assert error.value.detail["code"] == "calendar_conflicts"

    created = await api_create_event(EventCreate(
        title="Ранняя встреча",
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        allow_conflicts=True,
    ))
    assert created["status"] == "created"

    with pytest.raises(HTTPException) as update_error:
        await api_modify_event(created["uid"], EventUpdate(title="Изменённая ранняя встреча"))
    assert update_error.value.status_code == 409

    updated = await api_modify_event(
        created["uid"],
        EventUpdate(title="Изменённая ранняя встреча", allow_conflicts=True),
    )
    assert updated["status"] == "modified"
