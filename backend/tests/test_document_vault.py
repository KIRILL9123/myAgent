from pathlib import Path


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
