from pathlib import Path
import sqlite3

import pytest


def test_document_vault_ingest_search_and_deduplicate(tmp_path, monkeypatch):
    from backend.app.storage import db
    from backend.app.documents import document_service as service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "vault.db"))
    monkeypatch.setattr(service, "VAULT_DIR", Path(tmp_path / "files"))
    db.init_db()

    first = service.ingest_document(
        "vertrag.md",
        "Kündigungsfrist: 30 Tage. Ansprechpartner ist Anna.\n\nDie Probezeit endet am 31.08.2026.".encode("utf-8"),
        "text/markdown",
    )
    assert first["status"] == "ready"
    assert first["extracted_chars"] > 0
    assert first["metadata"]["extractor"] == "markitdown"
    assert first["metadata"]["format"] == "md"
    assert Path(tmp_path / "files" / first["stored_name"]).exists()

    matches = service.search_documents("Kündigungsfrist")
    assert matches and matches[0]["document_name"] == "vertrag.md"
    assert "30 Tage" in matches[0]["content"]

    duplicate = service.ingest_document("copy.md", b"Kundigungsfrist: 30 Tage", "text/markdown")
    assert duplicate["status"] == "ready"
    assert duplicate["id"] != first["id"]

    same = service.ingest_document(
        "other-name.md",
        "Kündigungsfrist: 30 Tage. Ansprechpartner ist Anna.\n\nDie Probezeit endet am 31.08.2026.".encode("utf-8"),
        "text/markdown",
    )
    assert same["id"] == first["id"]


def test_document_vault_is_separate_from_memory_and_retrieval_signal(tmp_path, monkeypatch):
    from backend.app.storage import db
    from backend.app.documents import document_service as service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "vault.db"))
    monkeypatch.setattr(service, "VAULT_DIR", Path(tmp_path / "files"))
    db.init_db()

    assert service.should_retrieve_documents("Что написано в моём договоре?")
    assert not service.should_retrieve_documents("Какая погода в Эрфурте?")
    assert service.is_document_inventory_request("Какие документы я загружал?")
    assert not service.is_document_inventory_request("Что написано в договоре?")
    assert service.list_documents() == []


@pytest.mark.asyncio
async def test_document_upload_reads_only_one_byte_over_limit(monkeypatch):
    from backend.app.api import documents as api
    from backend.app.documents import document_service as service

    monkeypatch.setattr(service, "MAX_DOCUMENT_BYTES", 8)

    class BoundedFile:
        filename = "oversized.md"
        content_type = "text/markdown"

        def __init__(self):
            self.read_sizes = []

        async def read(self, size=-1):
            self.read_sizes.append(size)
            return b"x" * size

    upload = BoundedFile()
    with pytest.raises(api.HTTPException) as exc_info:
        await api.api_upload_document(upload)

    assert exc_info.value.status_code == 400
    assert upload.read_sizes == [service.MAX_DOCUMENT_BYTES + 1]


def test_document_vault_cleans_file_after_unique_race(tmp_path, monkeypatch):
    from backend.app.storage import db
    from backend.app.documents import document_service as service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "vault.db"))
    files_dir = Path(tmp_path / "files")
    monkeypatch.setattr(service, "VAULT_DIR", files_dir)
    db.init_db()

    payload = b"Race-safe duplicate content"
    first = service.ingest_document("first.md", payload, "text/markdown")
    original_select = service._select_documents
    select_calls = 0

    def hide_existing_on_initial_check(where="", params=()):
        nonlocal select_calls
        select_calls += 1
        return [] if select_calls == 1 else original_select(where, params)

    monkeypatch.setattr(service, "_select_documents", hide_existing_on_initial_check)
    monkeypatch.setattr(service, "_insert_document", lambda *args: (_ for _ in ()).throw(sqlite3.IntegrityError("sha256")))

    duplicate = service.ingest_document("second.md", payload, "text/markdown")

    assert duplicate["id"] == first["id"]
    assert list(files_dir.iterdir()) == [files_dir / first["stored_name"]]


def test_document_vault_cleans_file_after_insert_failure(tmp_path, monkeypatch):
    from backend.app.storage import db
    from backend.app.documents import document_service as service

    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "vault.db"))
    files_dir = Path(tmp_path / "files")
    monkeypatch.setattr(service, "VAULT_DIR", files_dir)
    db.init_db()
    monkeypatch.setattr(service, "_insert_document", lambda *args: (_ for _ in ()).throw(RuntimeError("insert failed")))

    with pytest.raises(RuntimeError, match="insert failed"):
        service.ingest_document("broken.md", b"insert cleanup", "text/markdown")

    assert list(files_dir.iterdir()) == []
