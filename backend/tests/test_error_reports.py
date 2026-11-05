import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.storage import db


@pytest.fixture
def error_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "errors.db"))
    db.init_db()


def test_error_report_lifecycle_and_context_redaction(error_db):
    from backend.app.observability.error_reports import (
        create_error_report, list_error_reports, update_error_report,
    )

    report = create_error_report(
        "API timeout",
        "The backend did not answer in time.",
        severity="high",
        component="calendar",
        correlation_id="corr-123",
        error_type="TimeoutError",
        context={"endpoint": "/api/calendar", "attempt": 2, "secret": "drop-me"},
    )
    assert report["status"] == "new"
    assert report["context"] == {"endpoint": "/api/calendar", "attempt": 2}

    for status in ("fixing", "fixed", "verified", "closed"):
        report = update_error_report(report["id"], status, fix_reference="commit-1")
        assert report["status"] == status

    assert report["resolved_at"]
    listing = list_error_reports()
    assert listing["summary"]["closed"] == 1
    assert listing["reports"][0]["correlation_id"] == "corr-123"


def test_error_report_rejects_skipping_lifecycle(error_db):
    from backend.app.observability.error_reports import create_error_report, update_error_report

    report = create_error_report("Broken import")
    with pytest.raises(ValueError, match="invalid transition"):
        update_error_report(report["id"], "verified")


def test_error_report_api_exposes_list_and_create(error_db):
    from backend.app.api.errors import router

    app = FastAPI()
    app.include_router(router, prefix="/api/errors")
    client = TestClient(app)

    response = client.post("/api/errors", json={"title": "Manual report", "severity": "low"})
    assert response.status_code == 200
    report = response.json()
    assert report["status"] == "new"

    listing = client.get("/api/errors?status=new")
    assert listing.status_code == 200
    assert listing.json()["summary"]["new"] == 1
