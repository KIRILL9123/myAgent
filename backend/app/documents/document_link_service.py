"""Cross-domain links for Document Vault items.

Links keep the document as the source of provenance and point to an existing
domain entity. They intentionally do not copy task, calendar, or subscription
data into the document model.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any, Literal

from backend.app.commitments.commitment_service import get_commitment, list_commitments
from backend.app.documents.document_service import get_document
from backend.app.storage.db import get_db_connection
from backend.app.subscriptions.subscription_service import get_subscription, list_subscriptions

DocumentLinkType = Literal["commitment", "calendar_event", "subscription"]
ALLOWED_TARGET_TYPES = {"commitment", "calendar_event", "subscription"}
TARGET_PATHS = {
    "commitment": "/commitments",
    "calendar_event": "/calendar",
    "subscription": "/subscriptions",
}
TERMINAL_SUBSCRIPTION_STATUSES = {"CANCELLED", "EXPIRED"}


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id", "document_id", "target_type", "target_id", "target_label",
        "relationship", "created_by", "created_at",
    )
    item = dict(zip(keys, row))
    item["target_path"] = TARGET_PATHS[item["target_type"]]
    return item


def _get_link(link_id: int) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT id, document_id, target_type, target_id, target_label,
                      relationship, created_by, created_at
               FROM document_links WHERE id = ?""",
            (link_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_document_links(document_id: int) -> list[dict[str, Any]]:
    if not get_document(document_id):
        raise KeyError("document not found")
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT id, document_id, target_type, target_id, target_label,
                      relationship, created_by, created_at
               FROM document_links
               WHERE document_id = ?
               ORDER BY created_at DESC, id DESC""",
            (document_id,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _validate_target(target_type: str, target_id: str) -> None:
    if target_type == "commitment" and not get_commitment(target_id):
        raise KeyError("commitment not found")
    if target_type == "subscription" and not get_subscription(target_id):
        raise KeyError("subscription not found")
    # Calendar UIDs are provider-owned opaque identifiers. The target picker
    # only offers events returned by the configured provider, so we cannot
    # require a second lookup here (some CalDAV providers do not expose get-by-UID).


def create_document_link(
    document_id: int,
    target_type: DocumentLinkType | str,
    target_id: str,
    target_label: str,
    relationship: str = "related",
    created_by: str = "web",
) -> dict[str, Any]:
    document = get_document(document_id)
    if not document:
        raise KeyError("document not found")
    if document["status"] == "archived":
        raise ValueError("archived documents cannot receive links")

    normalized_type = str(target_type).strip().lower()
    normalized_id = str(target_id).strip()
    normalized_label = str(target_label).strip()
    normalized_relationship = str(relationship).strip() or "related"
    if normalized_type not in ALLOWED_TARGET_TYPES:
        raise ValueError(f"target_type must be one of {sorted(ALLOWED_TARGET_TYPES)}")
    if not normalized_id:
        raise ValueError("target_id must not be empty")
    if not normalized_label:
        raise ValueError("target_label must not be empty")
    if len(normalized_id) > 200 or len(normalized_label) > 300 or len(normalized_relationship) > 80:
        raise ValueError("document link fields are too long")
    _validate_target(normalized_type, normalized_id)

    with get_db_connection() as conn:
        existing = conn.execute(
            """SELECT id, document_id, target_type, target_id, target_label,
                      relationship, created_by, created_at
               FROM document_links
               WHERE document_id = ? AND target_type = ? AND target_id = ?""",
            (document_id, normalized_type, normalized_id),
        ).fetchone()
        if existing:
            return _row_to_dict(existing)
        cursor = conn.execute(
            """INSERT INTO document_links
               (document_id, target_type, target_id, target_label, relationship, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (document_id, normalized_type, normalized_id, normalized_label, normalized_relationship, created_by),
        )
        conn.commit()
        link_id = int(cursor.lastrowid)
    result = _get_link(link_id)
    assert result is not None
    return result


def delete_document_link(document_id: int, link_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM document_links WHERE id = ? AND document_id = ?",
            (link_id, document_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def _target(target_type: str, target_id: str, label: str, detail: str = "", status: str | None = None) -> dict[str, Any]:
    item = {
        "target_type": target_type,
        "id": str(target_id),
        "label": label,
        "detail": detail,
        "target_path": TARGET_PATHS[target_type],
    }
    if status:
        item["status"] = status
    return item


def list_document_link_targets() -> list[dict[str, Any]]:
    """Return current entities that can be linked from a document card."""
    targets: list[dict[str, Any]] = []

    for item in list_commitments(include_completed=False):
        detail = item.get("deadline_at") or item.get("status", "")
        targets.append(_target("commitment", item["id"], item["title"], str(detail), item.get("status")))

    for item in list_subscriptions():
        if item.get("status") in TERMINAL_SUBSCRIPTION_STATUSES:
            continue
        detail = item.get("next_charge_at") or item.get("status", "")
        targets.append(_target("subscription", item["id"], item["name"], str(detail), item.get("status")))

    now = datetime.now(timezone.utc)
    try:
        provider = os.getenv("CALENDAR_PROVIDER", "caldav").strip().lower()
        if provider in {"local", "sqlite"}:
            from backend.app.calendar.local_calendar import list_events as list_calendar_events
        else:
            from backend.app.calendar.calendar_service import list_events as list_calendar_events

        events = list_calendar_events(
            (now - timedelta(days=365)).isoformat(),
            (now + timedelta(days=365)).isoformat(),
        )
    except Exception:
        events = []
    if isinstance(events, list):
        for item in events:
            if not item.get("uid"):
                continue
            label = str(item.get("summary") or "Событие без названия").strip()
            detail = str(item.get("start") or "").strip()
            targets.append(_target("calendar_event", str(item.get("uid", "")), label, detail))

    return targets
