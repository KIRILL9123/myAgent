from backend.app.calendar import calendar_service
from backend.app.storage import db


def test_local_provider_is_shared_by_calendar_surfaces(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "calendar.db"))
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    monkeypatch.setenv("EXECUTION_MODE", "real")
    db.init_db()

    assert calendar_service.list_calendars() == [
        {"calendar_id": "local", "calendar_name": "Mira", "calendar_color": ""}
    ]

    created = calendar_service.create_event(
        title="Weekly review",
        start_datetime="2026-08-03T10:00:00",
        end_datetime="2026-08-03T11:00:00",
        recurrence="weekly",
        recurrence_until="2026-08-31",
        reminder_minutes=30,
    )

    listed = calendar_service.list_events("2026-08-24T00:00:00", "2026-08-25T00:00:00")
    assert listed == [
        {
            "uid": created["uid"],
            "summary": "Weekly review",
            "start": "2026-08-24T10:00:00",
            "end": "2026-08-24T11:00:00",
            "description": "",
            "recurrence": "weekly",
            "recurrence_until": "2026-08-31",
            "reminder_minutes": 30,
        }
    ]


def test_agent_calendar_writes_keep_dry_run_boundary(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "calendar.db"))
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    monkeypatch.setenv("EXECUTION_MODE", "dry_run")
    db.init_db()

    result = calendar_service.create_event(
        title="Should not be written",
        start_datetime="2026-08-03T10:00:00",
        enforce_execution_mode=True,
    )

    assert result["status"] == "dry_run"
    assert calendar_service.list_events("2026-08-03T00:00:00", "2026-08-04T00:00:00") == []
