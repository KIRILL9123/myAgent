from pathlib import Path

import pytest


def _setup_vault(tmp_path, monkeypatch):
    from backend.app.storage import db
    from backend.app.documents import document_service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "links.db"))
    monkeypatch.setattr(document_service, "VAULT_DIR", Path(tmp_path / "files"))
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    db.init_db()
    return document_service.ingest_document("brief.md", b"Project context and dates", "text/markdown")


def test_document_links_point_to_existing_domains_and_are_idempotent(tmp_path, monkeypatch):
    from backend.app.calendar.local_calendar import create_event
    from backend.app.commitments.commitment_service import create_active_commitment
    from backend.app.documents.document_link_service import (
        create_document_link,
        delete_document_link,
        list_document_link_targets,
        list_document_links,
    )
    from backend.app.subscriptions.subscription_service import create_subscription

    document = _setup_vault(tmp_path, monkeypatch)
    commitment = create_active_commitment("Send the brief")
    subscription = create_subscription("Reference plan")
    event = create_event("Brief review", "2026-08-05T10:00:00+00:00")

    links = [
        create_document_link(document["id"], "commitment", commitment["id"], commitment["title"]),
        create_document_link(document["id"], "subscription", subscription["id"], subscription["name"]),
        create_document_link(document["id"], "calendar_event", event["uid"], event["summary"]),
    ]
    assert {link["target_type"] for link in links} == {"commitment", "subscription", "calendar_event"}
    assert all(link["target_path"] for link in links)
    assert create_document_link(document["id"], "commitment", commitment["id"], "Renamed label")["id"] == links[0]["id"]
    assert len(list_document_links(document["id"])) == 3

    targets = list_document_link_targets()
    assert any(item["id"] == commitment["id"] and item["target_type"] == "commitment" for item in targets)
    assert any(item["id"] == subscription["id"] and item["target_type"] == "subscription" for item in targets)
    assert any(item["id"] == event["uid"] and item["target_type"] == "calendar_event" for item in targets)

    assert delete_document_link(document["id"], links[0]["id"])
    assert not delete_document_link(document["id"], links[0]["id"])
    assert len(list_document_links(document["id"])) == 2


def test_document_links_reject_unknown_or_archived_targets(tmp_path, monkeypatch):
    from backend.app.documents import document_link_service
    from backend.app.documents.document_service import archive_document

    document = _setup_vault(tmp_path, monkeypatch)
    with pytest.raises(KeyError, match="commitment not found"):
        document_link_service.create_document_link(document["id"], "commitment", "missing", "Missing")

    assert archive_document(document["id"])
    with pytest.raises(ValueError, match="archived"):
        document_link_service.create_document_link(document["id"], "calendar_event", "event-1", "Event")
