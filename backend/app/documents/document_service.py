from __future__ import annotations

import hashlib
import html
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from backend.app.storage.db import get_db_connection


VAULT_DIR = Path(os.environ.get("DOCUMENT_VAULT_DIR") or Path(__file__).resolve().parents[2] / "document_vault")
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_CHARS = 2_000_000
CHUNK_SIZE = 1_200
CHUNK_OVERLAP = 160
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm", ".pdf"}


def _safe_name(filename: str) -> str:
    name = Path(filename or "document").name.strip()
    name = re.sub(r"[^\w.()\- ]+", "_", name, flags=re.UNICODE).strip(" .")
    return (name or "document")[:240]


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _extract_text(filename: str, payload: bytes) -> tuple[str, dict[str, Any]]:
    extension = _extension(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Поддерживаются TXT, Markdown, CSV, JSON, HTML и PDF")

    if extension == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("Для PDF нужен пакет pypdf. Установите зависимости проекта и повторите загрузку.") from exc
        import io

        reader = PdfReader(io.BytesIO(payload))
        pages: list[str] = []
        for index, page in enumerate(reader.pages):
            pages.append(f"[Страница {index + 1}]\n{page.extract_text() or ''}")
        return "\n\n".join(pages), {"pages": len(reader.pages), "extractor": "pypdf"}

    text = payload.decode("utf-8-sig", errors="replace")
    if extension in {".html", ".htm"}:
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
    elif extension == ".json":
        try:
            text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return text, {"extractor": "text"}


def _chunks(text: str) -> list[tuple[int, int, str]]:
    normalized = text.replace("\x00", "").strip()
    if not normalized:
        return []
    if len(normalized) > MAX_EXTRACTED_CHARS:
        normalized = normalized[:MAX_EXTRACTED_CHARS]
    result: list[tuple[int, int, str]] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + CHUNK_SIZE)
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start, end), normalized.rfind(" ", start, end))
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary
        chunk = normalized[start:end].strip()
        if chunk:
            result.append((start, end, chunk))
        if end >= len(normalized):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return result


def _row(row: Any) -> dict[str, Any]:
    keys = ["id", "original_name", "stored_name", "mime_type", "extension", "size_bytes", "sha256", "status", "error_message", "extracted_chars", "metadata_json", "created_at", "updated_at"]
    item = dict(zip(keys, row))
    try:
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    except json.JSONDecodeError:
        item["metadata"] = {}
        item.pop("metadata_json", None)
    return item


def _select_documents(where: str = "", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, original_name, stored_name, mime_type, extension, size_bytes,
                      sha256, status, error_message, extracted_chars, metadata_json,
                      created_at, updated_at
               FROM documents """ + where + " ORDER BY created_at DESC", params
        ).fetchall()
    return [_row(row) for row in rows]


def list_documents(status: str = "active") -> list[dict[str, Any]]:
    if status == "all":
        return _select_documents()
    if status not in {"active", "ready", "failed", "archived"}:
        raise ValueError("Invalid document status")
    where = "WHERE status != 'archived'" if status == "active" else "WHERE status = ?"
    return _select_documents(where, () if status == "active" else (status,))


def get_document(document_id: int) -> dict[str, Any] | None:
    rows = _select_documents("WHERE id = ?", (document_id,))
    return rows[0] if rows else None


def ingest_document(filename: str, payload: bytes, mime_type: str = "application/octet-stream") -> dict[str, Any]:
    original_name = _safe_name(filename)
    if not payload:
        raise ValueError("Файл пустой")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise ValueError("Максимальный размер документа — 20 MB")
    extension = _extension(original_name)
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Поддерживаются TXT, Markdown, CSV, JSON, HTML и PDF")

    digest = hashlib.sha256(payload).hexdigest()
    existing = _select_documents("WHERE sha256 = ?", (digest,))
    if existing:
        return existing[0]

    stored_name = f"{uuid.uuid4().hex}{extension}"
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    target = VAULT_DIR / stored_name
    target.write_bytes(payload)
    extracted = ""
    metadata: dict[str, Any] = {"original_name": original_name}
    status = "ready"
    error_message = None
    try:
        extracted, extraction_metadata = _extract_text(original_name, payload)
        metadata.update(extraction_metadata)
        chunks = _chunks(extracted)
        if not chunks:
            raise ValueError("В документе не найден текст для поиска")
    except Exception as exc:
        chunks = []
        status = "failed"
        error_message = str(exc)[:500]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO documents
               (original_name, stored_name, mime_type, extension, size_bytes, sha256,
                status, error_message, extracted_chars, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (original_name, stored_name, mime_type or "application/octet-stream", extension,
             len(payload), digest, status, error_message, len(extracted), json.dumps(metadata, ensure_ascii=False)),
        )
        document_id = cursor.lastrowid
        if status == "ready":
            for index, (start, end, content) in enumerate(chunks):
                cursor.execute(
                    "INSERT INTO document_chunks (document_id, chunk_index, content, start_char, end_char) VALUES (?, ?, ?, ?, ?)",
                    (document_id, index, content, start, end),
                )
                chunk_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO document_chunks_fts (content, document_id, chunk_id) VALUES (?, ?, ?)",
                    (content, document_id, chunk_id),
                )
        conn.commit()
    result = get_document(int(document_id))
    assert result is not None
    return result


def archive_document(document_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.execute("UPDATE documents SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status != 'archived'", (document_id,))
        conn.commit()
        return cursor.rowcount > 0


def search_documents(query: str, limit: int = 8) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []
    limit = max(1, min(limit, 20))
    tokens = re.findall(r"[\w\-]{2,}", query, flags=re.UNICODE)
    if not tokens:
        return []
    match_query = " AND ".join(f'"{token.replace(chr(34), "")}"' for token in tokens[:12])
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT f.document_id, f.chunk_id, f.content, d.original_name,
                      d.mime_type, d.created_at, bm25(document_chunks_fts) AS score
               FROM document_chunks_fts f
               JOIN documents d ON d.id = f.document_id
               WHERE document_chunks_fts MATCH ? AND d.status = 'ready'
               ORDER BY score LIMIT ?""",
            (match_query, limit),
        ).fetchall()
    return [{"document_id": row[0], "chunk_id": row[1], "content": row[2], "document_name": row[3], "mime_type": row[4], "created_at": row[5], "score": row[6]} for row in rows]


def should_retrieve_documents(query: str) -> bool:
    lowered = (query or "").lower()
    cues = ("документ", "файл", "pdf", "договор", "инструкци", "материал", "в заметках", "document", "file", "contract", "manual")
    return any(cue in lowered for cue in cues)


def is_document_inventory_request(query: str) -> bool:
    lowered = (query or "").lower()
    inventory_cues = (
        "какие документы", "какие файлы", "что я загружал", "что загружено",
        "список документов", "список файлов", "покажи документы", "покажи файлы",
        "which documents", "which files", "uploaded files", "list documents", "list files",
    )
    return any(cue in lowered for cue in inventory_cues)


def build_document_inventory_context(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "В Document Vault нет активных документов."
    lines = ["Активные документы в Document Vault:"]
    for document in documents:
        lines.append(
            f"- {document['original_name']} ({document['extension']}, "
            f"{document['extracted_chars']} символов, добавлен {document['created_at']})"
        )
    return "\n".join(lines)


def build_document_context(results: list[dict[str, Any]], max_chars: int = 6_000) -> str:
    blocks: list[str] = []
    total = 0
    for item in results:
        block = f"Источник документа: {item['document_name']}\n{item['content']}"
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)
