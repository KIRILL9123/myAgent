from backend.app.calendar.local_calendar import (
    create_event,
    delete_event,
    list_events,
    modify_event,
)
from backend.app.storage import db


def test_local_calendar_crud(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "calendar.db"))
    db.init_db()

    created = create_event(
        title="Командный созвон",
        start_datetime="2026-08-03T10:00:00",
        end_datetime="2026-08-03T11:00:00",
        description="Проверка локального календаря",
    )
    assert created["status"] == "created"

    listed = list_events("2026-08-03T00:00:00", "2026-08-03T23:59:59")
    assert listed == [{
        "uid": created["uid"],
        "summary": "Командный созвон",
        "start": "2026-08-03T10:00:00",
        "end": "2026-08-03T11:00:00",
        "description": "Проверка локального календаря",
    }]

    updated = modify_event(created["uid"], {"title": "Обновлённый созвон"})
    assert updated["status"] == "modified"
    assert updated["summary"] == "Обновлённый созвон"

    recurring = create_event(
        title="Birthday",
        start_datetime="2026-08-03T00:00:00",
        all_day=True,
        recurrence="yearly",
        recurrence_until="2028-08-03",
    )
    future = list_events("2027-08-03T00:00:00", "2027-08-04T00:00:00")
    assert future == [{
        "uid": recurring["uid"],
        "summary": "Birthday",
        "start": "2027-08-03T00:00:00",
        "end": "2027-08-04T00:00:00",
        "description": "",
        "all_day": True,
        "recurrence": "yearly",
        "recurrence_until": "2028-08-03",
    }]

    deleted = delete_event(created["uid"])
    assert deleted["status"] == "deleted"
    assert delete_event(recurring["uid"])["status"] == "deleted"
    assert list_events("2026-08-03T00:00:00", "2026-08-03T23:59:59") == []
