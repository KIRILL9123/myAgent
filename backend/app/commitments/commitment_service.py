import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection

STATUSES = {"PROPOSED", "ACTIVE", "COMPLETED", "CANCELLED", "EXPIRED"}
SOURCE_TYPES = {"CHAT", "EMAIL", "DOCUMENT", "CALENDAR"}
TERMINAL_STATUSES = {"COMPLETED", "CANCELLED"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_datetime(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _json(value: Any, default: Any) -> str:
    return json.dumps(default if value is None else value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    keys = (
        "id", "title", "description", "status", "confidence", "provenance",
        "source_type", "source_ref", "owner", "deadline_at", "reminder_at",
        "reminder_sent_at", "created_at", "updated_at", "activated_at",
        "completed_at", "cancelled_at", "expired_at", "approval_provenance",
        "related_fact_ids", "related_calendar_event_ids", "conflicts_with_ids",
    )
    result = dict(zip(keys, row))
    for key in (
        "provenance", "approval_provenance", "related_fact_ids",
        "related_calendar_event_ids", "conflicts_with_ids",
    ):
        default = [] if key.endswith("_ids") else (None if key == "approval_provenance" else {})
        result[key] = _loads(result[key], default)
    return result


def _get(commitment_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT id, title, description, status, confidence, provenance_json,
                      source_type, source_ref, owner, deadline_at, reminder_at,
                      reminder_sent_at, created_at, updated_at, activated_at,
                      completed_at, cancelled_at, expired_at, approval_provenance_json,
                      related_fact_ids_json, related_calendar_event_ids_json,
                      conflicts_with_ids_json
               FROM commitments WHERE id = ?""",
            (commitment_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def _record_event(conn, commitment_id: str, event_type: str,
                  from_status: str | None, to_status: str | None,
                  payload: dict[str, Any] | None = None) -> None:
    conn.execute(
        """INSERT INTO commitment_events
           (commitment_id, event_type, from_status, to_status, payload_json)
           VALUES (?, ?, ?, ?, ?)""",
        (commitment_id, event_type, from_status, to_status, _json(payload, {})),
    )


def create_commitment(
    title: str,
    description: str | None = None,
    source_type: str = "CHAT",
    source_ref: str | None = None,
    owner: str = "user",
    deadline_at: str | None = None,
    reminder_at: str | None = None,
    confidence: float = 1.0,
    provenance: dict[str, Any] | None = None,
    related_fact_ids: list[int] | None = None,
    related_calendar_event_ids: list[str] | None = None,
    conflicts_with_ids: list[str] | None = None,
) -> dict[str, Any]:
    title = title.strip()
    source_type = source_type.upper()
    if not title:
        raise ValueError("title must not be empty")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    deadline_at = _validate_datetime(deadline_at, "deadline_at")
    reminder_at = _validate_datetime(reminder_at, "reminder_at")
    if deadline_at and reminder_at and reminder_at > deadline_at:
        raise ValueError("reminder_at must be before deadline_at")

    commitment_id = str(uuid.uuid4())
    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO commitments
               (id, title, description, confidence, provenance_json, source_type,
                source_ref, owner, deadline_at, reminder_at, related_fact_ids_json,
                related_calendar_event_ids_json, conflicts_with_ids_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (commitment_id, title, description, confidence, _json(provenance, {}),
             source_type, source_ref, owner.strip() or "user", deadline_at, reminder_at,
             _json(related_fact_ids, []), _json(related_calendar_event_ids, []),
             _json(conflicts_with_ids, []), now, now),
        )
        _record_event(conn, commitment_id, "CREATED", None, "PROPOSED", {
            "source_type": source_type, "source_ref": source_ref,
        })
        conn.commit()
    return _get(commitment_id)  # type: ignore[return-value]


def list_commitments(status: str | None = None, owner: str | None = None,
                     include_completed: bool = True) -> list[dict[str, Any]]:
    if status and status.upper() not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status.upper())
    elif not include_completed:
        clauses.append("status NOT IN ('COMPLETED', 'CANCELLED')")
    if owner:
        clauses.append("owner = ?")
        params.append(owner)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""SELECT id, title, description, status, confidence, provenance_json,
                       source_type, source_ref, owner, deadline_at, reminder_at,
                       reminder_sent_at, created_at, updated_at, activated_at,
                       completed_at, cancelled_at, expired_at, approval_provenance_json,
                       related_fact_ids_json, related_calendar_event_ids_json,
                       conflicts_with_ids_json
                FROM commitments {where}
                ORDER BY CASE WHEN deadline_at IS NULL THEN 1 ELSE 0 END, deadline_at, created_at""",
            params,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_commitment(commitment_id: str) -> dict[str, Any] | None:
    return _get(commitment_id)


def update_commitment(commitment_id: str, **changes: Any) -> dict[str, Any]:
    commitment = _get(commitment_id)
    if not commitment:
        raise KeyError("commitment not found")
    if commitment["status"] in TERMINAL_STATUSES:
        raise ValueError("terminal commitments cannot be edited")
    allowed = {"title", "description", "owner", "deadline_at", "reminder_at", "confidence"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")
    if "title" in changes:
        changes["title"] = str(changes["title"]).strip()
        if not changes["title"]:
            raise ValueError("title must not be empty")
    if "deadline_at" in changes:
        changes["deadline_at"] = _validate_datetime(changes["deadline_at"], "deadline_at")
    if "reminder_at" in changes:
        changes["reminder_at"] = _validate_datetime(changes["reminder_at"], "reminder_at")
    deadline = changes.get("deadline_at", commitment["deadline_at"])
    reminder = changes.get("reminder_at", commitment["reminder_at"])
    if deadline and reminder and reminder > deadline:
        raise ValueError("reminder_at must be before deadline_at")
    if "confidence" in changes and not 0.0 <= changes["confidence"] <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    if not changes:
        return commitment
    assignments = ", ".join(f"{key} = ?" for key in changes)
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE commitments SET {assignments}, updated_at = ? WHERE id = ?",
            [*changes.values(), _now(), commitment_id],
        )
        _record_event(conn, commitment_id, "UPDATED", commitment["status"], commitment["status"], {
            "fields": sorted(changes),
        })
        conn.commit()
    return _get(commitment_id)  # type: ignore[return-value]


def transition_commitment(commitment_id: str, action: str,
                          approval_provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    commitment = _get(commitment_id)
    if not commitment:
        raise KeyError("commitment not found")
    current = commitment["status"]
    transitions = {
        "approve": ("ACTIVE", {"PROPOSED"}),
        "complete": ("COMPLETED", {"ACTIVE"}),
        "cancel": ("CANCELLED", {"PROPOSED", "ACTIVE", "EXPIRED"}),
        "reopen": ("ACTIVE", {"EXPIRED"}),
        "expire": ("EXPIRED", {"ACTIVE"}),
    }
    if action not in transitions:
        raise ValueError(f"unsupported action: {action}")
    target, allowed = transitions[action]
    if current not in allowed:
        raise ValueError(f"cannot {action} commitment in {current} status")
    now = _now()
    timestamp_field = {
        "ACTIVE": "activated_at", "COMPLETED": "completed_at",
        "CANCELLED": "cancelled_at", "EXPIRED": "expired_at",
    }[target]
    fields = [f"status = ?", "updated_at = ?", f"{timestamp_field} = ?"]
    values: list[Any] = [target, now, now]
    if action == "approve":
        fields.append("approval_provenance_json = ?")
        values.append(_json(approval_provenance, {}))
    values.append(commitment_id)
    with get_db_connection() as conn:
        conn.execute(f"UPDATE commitments SET {', '.join(fields)} WHERE id = ?", values)
        _record_event(conn, commitment_id, action.upper(), current, target, {
            "approval_provenance": approval_provenance,
        } if approval_provenance else None)
        conn.commit()
    return _get(commitment_id)  # type: ignore[return-value]


def expire_overdue(now: str | None = None) -> list[dict[str, Any]]:
    cutoff = _validate_datetime(now, "now") if now else _now()
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM commitments WHERE status = 'ACTIVE' AND deadline_at IS NOT NULL AND deadline_at < ?",
            (cutoff,),
        ).fetchall()
    expired = []
    for (commitment_id,) in rows:
        expired.append(transition_commitment(commitment_id, "expire"))
    return [item for item in expired if item is not None]


def get_commitment_events(commitment_id: str) -> list[dict[str, Any]]:
    if not _get(commitment_id):
        raise KeyError("commitment not found")
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, event_type, from_status, to_status, payload_json, created_at FROM commitment_events WHERE commitment_id = ? ORDER BY id",
            (commitment_id,),
        ).fetchall()
    return [
        {"id": row[0], "event_type": row[1], "from_status": row[2],
         "to_status": row[3], "payload": _loads(row[4], {}), "created_at": row[5]}
        for row in rows
    ]
