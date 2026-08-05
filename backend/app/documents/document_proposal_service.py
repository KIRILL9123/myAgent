"""Deterministic, approval-gated actions suggested by document evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

from backend.app.approvals.approval_service import create_document_proposal_request
from backend.app.documents.document_link_service import create_document_link
from backend.app.documents.document_service import get_document
from backend.app.storage.db import get_db_connection

DocumentActionType = Literal["commitment", "calendar_event"]
ACTION_TYPES = {"commitment", "calendar_event"}

_DATE_PATTERN = re.compile(
    r"(?P<iso>\b\d{4}-\d{1,2}-\d{1,2}\b)|"
    r"(?P<dmy>\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b)|"
    r"(?P<month>\b\d{1,2}\.\s*(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember|january|february|march|may|june|july|august|september|october|november|december)\s+\d{4}\b)",
    re.IGNORECASE,
)
_OBLIGATION_PATTERN = re.compile(
    r"(?:\b(?:необходимо|нужно|обязан(?:а|о|ы)?|обязательство|срок|оплатить|продлить|предоставить|отправить|подать|передать|зарегистрировать|"
    r"muss|müssen|pflicht|frist|zahlen|verlängern|einreichen|vorlegen|übermitteln|"
    r"must|deadline|pay|renew|submit|provide|send|register)\b)",
    re.IGNORECASE,
)
_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6,
    "july": 7, "october": 10, "december": 12,
}


def _read_document_text(document_id: int) -> str:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT content FROM document_chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
    return "\n".join(str(row[0]) for row in rows)


def _parse_date(value: str) -> date | None:
    normalized = value.strip().lower().replace(" ", " ")
    try:
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", normalized):
            return datetime.strptime(normalized, "%Y-%m-%d").date()
        if re.fullmatch(r"\d{1,2}[./-]\d{1,2}[./-]\d{4}", normalized):
            separator = "." if "." in normalized else "/" if "/" in normalized else "-"
            day, month, year = (int(part) for part in normalized.split(separator))
            return date(year, month, day)
        match = re.fullmatch(r"(\d{1,2})\.\s*([\wäöüß]+)\s+(\d{4})", normalized, re.IGNORECASE)
        if match:
            return date(int(match.group(3)), _MONTHS[match.group(2)], int(match.group(1)))
    except (KeyError, ValueError):
        return None
    return None


def _to_deadline(value: date) -> str:
    return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()


def _candidate_id(document_id: int, evidence: str, deadline_at: str) -> str:
    raw = f"{document_id}|{evidence}|{deadline_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _fragments(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", fragment).strip(" -•\t")
        for fragment in re.split(r"(?:\r?\n+|(?<=[.!?])\s+)", text)
        if fragment.strip()
    ]


def extract_document_candidates(document_id: int) -> list[dict[str, Any]]:
    document = get_document(document_id)
    if not document:
        raise KeyError("document not found")
    if document["status"] != "ready":
        raise ValueError("Документ ещё не готов для анализа")

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fragment in _fragments(_read_document_text(document_id)):
        if not _OBLIGATION_PATTERN.search(fragment):
            continue
        for match in _DATE_PATTERN.finditer(fragment):
            parsed = _parse_date(match.group(0))
            if parsed is None:
                continue
            evidence = fragment[:500]
            deadline_at = _to_deadline(parsed)
            candidate_id = _candidate_id(document_id, evidence, deadline_at)
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            title = re.sub(r"\s+", " ", fragment).strip(" .:;-")[:140]
            candidates.append({
                "candidate_id": candidate_id,
                "title": title or "Обязательство из документа",
                "evidence": evidence,
                "deadline_at": deadline_at,
                "date_label": parsed.isoformat(),
                "confidence": 0.88,
            })
            break
        if len(candidates) >= 20:
            break
    return candidates


def _proposal_row(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = ("id", "source_id", "title", "summary", "payload_json", "source_channel", "status", "created_at", "resolved_at")
    item = dict(zip(keys, row))
    try:
        payload = json.loads(item.pop("payload_json") or "{}")
    except json.JSONDecodeError:
        payload = {}
    item["payload"] = payload
    item["document_id"] = payload.get("document_id")
    item["candidate_id"] = payload.get("candidate_id")
    item["action_type"] = payload.get("action_type")
    return item


def list_document_proposals(document_id: int) -> list[dict[str, Any]]:
    if not get_document(document_id):
        raise KeyError("document not found")
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, source_id, title, summary, payload_json, source_channel,
                      status, created_at, resolved_at
               FROM approval_requests WHERE kind = 'DOCUMENT_PROPOSAL'
               ORDER BY created_at DESC""",
        ).fetchall()
    return [item for row in rows if (item := _proposal_row(row)).get("document_id") == document_id]


def scan_document_proposals(document_id: int) -> dict[str, Any]:
    document = get_document(document_id)
    if not document:
        raise KeyError("document not found")
    return {
        "document_id": document_id,
        "document_name": document["original_name"],
        "candidates": extract_document_candidates(document_id),
        "proposals": list_document_proposals(document_id),
    }


def create_document_proposal(
    document_id: int,
    candidate_id: str,
    action_type: DocumentActionType | str,
    source_channel: str = "web",
) -> dict[str, Any]:
    normalized_type = str(action_type).strip().lower()
    if normalized_type not in ACTION_TYPES:
        raise ValueError(f"action_type must be one of {sorted(ACTION_TYPES)}")
    candidate = next((item for item in extract_document_candidates(document_id) if item["candidate_id"] == candidate_id), None)
    if not candidate:
        raise ValueError("Предложение документа устарело или не найдено")
    document = get_document(document_id)
    assert document is not None
    source_id = f"{document_id}:{candidate_id}:{normalized_type}"
    title_prefix = "Создать задачу" if normalized_type == "commitment" else "Добавить событие"
    title = f"{title_prefix}: {candidate['title'][:100]}"
    summary = f"Найдено в «{document['original_name']}»: {candidate['evidence']}"
    payload = {
        "document_id": document_id,
        "document_name": document["original_name"],
        "candidate_id": candidate["candidate_id"],
        "action_type": normalized_type,
        "suggested_title": candidate["title"],
        "evidence": candidate["evidence"],
        "deadline_at": candidate["deadline_at"],
        "confidence": candidate["confidence"],
    }
    approval_id = create_document_proposal_request(source_id, title, summary, payload, source_channel)
    proposal = next(item for item in list_document_proposals(document_id) if item["id"] == approval_id)
    return {"status": "pending_approval", "proposal": proposal}


def apply_document_proposal(request: dict[str, Any], approval_id: str) -> dict[str, Any]:
    payload = request.get("payload") or {}
    document_id = int(payload.get("document_id"))
    action_type = payload.get("action_type")
    title = str(payload.get("suggested_title") or "Обязательство из документа").strip()
    deadline_at = str(payload.get("deadline_at") or "")
    evidence = str(payload.get("evidence") or "").strip()
    document = get_document(document_id)
    if not document:
        raise ValueError("Документ-источник больше не найден")
    if action_type == "commitment":
        from backend.app.commitments.commitment_service import create_active_commitment, list_commitments_by_source_prefix

        source_ref = f"document-proposal:{approval_id}"
        existing = list_commitments_by_source_prefix(source_ref)
        commitment = existing[0] if existing else create_active_commitment(
            title=title,
            description=evidence,
            source_type="DOCUMENT",
            source_ref=source_ref,
            deadline_at=deadline_at,
            provenance={"document_id": document_id, "evidence": evidence},
            approval_provenance={"approval_id": approval_id, "source": "document_vault"},
        )
        link = create_document_link(document_id, "commitment", commitment["id"], commitment["title"], relationship="derived")
        return {"status": "created", "action_type": action_type, "commitment": commitment, "link": link}
    if action_type == "calendar_event":
        from backend.app.calendar.calendar_service import create_event

        created = create_event(
            title=title,
            start_datetime=deadline_at,
            description=evidence,
            all_day=True,
            enforce_execution_mode=True,
        )
        if created.get("status") == "dry_run":
            raise ValueError("Календарь работает в безопасном режиме: событие не было сохранено")
        event_uid = created.get("uid")
        if not event_uid:
            raise ValueError("Календарь не вернул идентификатор события")
        link = create_document_link(document_id, "calendar_event", str(event_uid), title, relationship="derived")
        return {"status": "created", "action_type": action_type, "event": created, "link": link}
    raise ValueError("Неизвестный тип документного предложения")
