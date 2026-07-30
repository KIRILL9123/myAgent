from backend.app.observability.telemetry import (
    get_recent_events,
    get_telemetry_summary,
    record_event,
)
from backend.app.storage import db


def test_structured_telemetry_summary_and_redaction(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "observability.db"))
    db.init_db()

    record_event(
        "test_event", "test", "success", 12.345,
        {"safe_value": "ok", "content": "must not be stored"},
        correlation_id="corr-test",
    )

    summary = get_telemetry_summary()
    assert summary["total_events"] == 1
    assert summary["error_events"] == 0
    assert summary["groups"][0]["avg_duration_ms"] == 12.35

    recent = get_recent_events()
    assert recent[0]["correlation_id"] == "corr-test"
    assert recent[0]["payload"] == {"safe_value": "ok"}
