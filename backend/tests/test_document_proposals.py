from pathlib import Path

import pytest


def _setup_document(tmp_path, monkeypatch, text: str):
    from backend.app.storage import db
    from backend.app.documents import document_service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "proposals.db"))
    monkeypatch.setattr(document_service, "VAULT_DIR", Path(tmp_path / "files"))
    monkeypatch.setenv("CALENDAR_PROVIDER", "local")
    monkeypatch.setenv("EXECUTION_MODE", "real")
    db.init_db()
    return document_service.ingest_document("vertrag.md", text.encode("utf-8"), "text/markdown")


@pytest.mark.asyncio
async def test_document_obligation_becomes_approval_gated_commitment(tmp_path, monkeypatch):
    from backend.app.approvals.approval_service import list_approvals, resolve_approval
    from backend.app.commitments.commitment_service import list_commitments
    from backend.app.documents.document_link_service import list_document_links
    from backend.app.documents.document_proposal_service import create_document_proposal, scan_document_proposals

    document = _setup_document(tmp_path, monkeypatch, "Оплатить счёт до 31.08.2026.\nСпасибо.")
    scan = scan_document_proposals(document["id"])
    assert len(scan["candidates"]) == 1
    candidate = scan["candidates"][0]
    assert candidate["date_label"] == "2026-08-31"

    created = create_document_proposal(document["id"], candidate["candidate_id"], "commitment")
    approval = created["proposal"]
    assert approval["status"] == "PENDING"
    assert approval["action_type"] == "commitment"
    assert list_approvals()[0]["kind"] == "DOCUMENT_PROPOSAL"

    resolved = await resolve_approval(approval["id"], "approve")
    assert resolved["status"] == "APPROVED"
    tasks = list_commitments(status="ACTIVE")
    assert len(tasks) == 1
    assert tasks[0]["source_type"] == "DOCUMENT"
    assert tasks[0]["deadline_at"].startswith("2026-08-31")
    assert list_document_links(document["id"])[0]["target_type"] == "commitment"


@pytest.mark.asyncio
async def test_document_obligation_can_be_approved_as_local_calendar_event(tmp_path, monkeypatch):
    from backend.app.approvals.approval_service import resolve_approval
    from backend.app.calendar.local_calendar import list_events
    from backend.app.documents.document_proposal_service import create_document_proposal, scan_document_proposals

    document = _setup_document(tmp_path, monkeypatch, "Submit the form by 2026-09-05.")
    candidate = scan_document_proposals(document["id"])["candidates"][0]
    approval = create_document_proposal(document["id"], candidate["candidate_id"], "calendar_event")["proposal"]

    resolved = await resolve_approval(approval["id"], "approve")
    assert resolved["status"] == "APPROVED"
    events = list_events("2026-09-04T00:00:00+00:00", "2026-09-06T00:00:00+00:00")
    assert len(events) == 1
    assert events[0]["summary"].startswith("Submit the form")


def test_document_proposal_is_idempotent(tmp_path, monkeypatch):
    from backend.app.approvals.approval_service import list_approvals
    from backend.app.documents.document_proposal_service import create_document_proposal, scan_document_proposals

    document = _setup_document(tmp_path, monkeypatch, "Нужно предоставить справку до 15.09.2026.")
    candidate = scan_document_proposals(document["id"])["candidates"][0]
    first = create_document_proposal(document["id"], candidate["candidate_id"], "commitment")["proposal"]
    second = create_document_proposal(document["id"], candidate["candidate_id"], "commitment")["proposal"]
    assert first["id"] == second["id"]
    assert len(list_approvals()) == 1
