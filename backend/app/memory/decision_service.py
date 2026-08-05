"""Structured Decision Journal records owned by the Knowledge domain."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection

DECISION_STATUSES = {"ACTIVE", "REVISIT", "SUPERSEDED", "ARCHIVED"}
SOURCE_TYPES = {"MANUAL", "CHAT", "TELEGRAM", "DOCUMENT"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _datetime(value: str | None, field: str) -> str | None:
    if value is None or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _json(value: Any, default: Any) -> str:
    return json.dumps(default if value is None else value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def _row(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = ("id", "title", "decision_text", "rationale", "alternatives", "status", "decided_at", "review_at", "source_type", "provenance", "created_at", "updated_at")
    result = dict(zip(keys, row))
    result["alternatives"] = _loads(result["alternatives"], [])
    result["provenance"] = _loads(result["provenance"], {})
    return result


def _get(decision_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, title, decision_text, rationale, alternatives_json, status, decided_at, review_at, source_type, provenance_json, created_at, updated_at FROM decisions WHERE id = ?", (decision_id,)).fetchone()
    return _row(row) if row else None


def create_decision(title: str, decision_text: str, rationale: str | None = None,
                    alternatives: list[str] | None = None, status: str = "ACTIVE",
                    decided_at: str | None = None, review_at: str | None = None,
                    source_type: str = "MANUAL", provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    title, decision_text = title.strip(), decision_text.strip()
    status, source_type = status.upper(), source_type.upper()
    if not title or not decision_text:
        raise ValueError("title and decision_text must not be empty")
    if status not in DECISION_STATUSES:
        raise ValueError(f"status must be one of {sorted(DECISION_STATUSES)}")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
    decided_at, review_at = _datetime(decided_at, "decided_at"), _datetime(review_at, "review_at")
    decision_id, now = str(uuid.uuid4()), _now()
    with get_db_connection() as conn:
        conn.execute("INSERT INTO decisions (id, title, decision_text, rationale, alternatives_json, status, decided_at, review_at, source_type, provenance_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (decision_id, title, decision_text, rationale, _json(alternatives, []), status, decided_at, review_at, source_type, _json(provenance, {}), now, now))
        conn.commit()
    return _get(decision_id)  # type: ignore[return-value]


def list_decisions(status: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    if status and status.upper() not in DECISION_STATUSES:
        raise ValueError(f"status must be one of {sorted(DECISION_STATUSES)}")
    clauses, params = [], []
    if status:
        clauses.append("status = ?"); params.append(status.upper())
    if query:
        clauses.append("(title LIKE ? OR decision_text LIKE ? OR rationale LIKE ?)")
        needle = f"%{query}%"; params.extend([needle, needle, needle])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as conn:
        rows = conn.execute(f"SELECT id, title, decision_text, rationale, alternatives_json, status, decided_at, review_at, source_type, provenance_json, created_at, updated_at FROM decisions {where} ORDER BY CASE WHEN review_at IS NULL THEN 1 ELSE 0 END, review_at, updated_at DESC", params).fetchall()
    return [_row(item) for item in rows]


def update_decision(decision_id: str, **changes: Any) -> dict[str, Any]:
    current = _get(decision_id)
    if not current:
        raise KeyError("decision not found")
    allowed = {"title", "decision_text", "rationale", "alternatives", "status", "decided_at", "review_at"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")
    for key in ("title", "decision_text"):
        if key in changes:
            changes[key] = str(changes[key]).strip()
            if not changes[key]:
                raise ValueError(f"{key} must not be empty")
    if "status" in changes:
        changes["status"] = str(changes["status"]).upper()
        if changes["status"] not in DECISION_STATUSES:
            raise ValueError(f"status must be one of {sorted(DECISION_STATUSES)}")
    if "decided_at" in changes:
        changes["decided_at"] = _datetime(changes["decided_at"], "decided_at")
    if "review_at" in changes:
        changes["review_at"] = _datetime(changes["review_at"], "review_at")
    if "alternatives" in changes:
        changes["alternatives"] = _json(changes["alternatives"], [])
    if not changes:
        return current
    now = _now()
    assignments = ", ".join(f"{('alternatives_json' if key == 'alternatives' else key)} = ?" for key in changes)
    with get_db_connection() as conn:
        conn.execute(f"UPDATE decisions SET {assignments}, updated_at = ? WHERE id = ?", [*changes.values(), now, decision_id])
        conn.commit()
    return _get(decision_id)  # type: ignore[return-value]
