"""Persistent user interactions with the read-only Action Center projection.

The table stores only presentation state. Domain records remain authoritative:
completion, cancellation, approval and rescheduling always go through their
own services.
"""

from datetime import datetime, timezone
from typing import Any

from backend.app.storage.db import get_db_connection

ACTION_STATES = {"read", "snoozed", "dismissed"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalise_until(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("snoozed_until must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def set_action_state(
    action_id: str,
    state: str,
    *,
    snoozed_until: str | datetime | None = None,
) -> dict[str, Any]:
    """Set projection state for one action id, or clear it with ``unread``."""
    action_id = action_id.strip()
    if not action_id:
        raise ValueError("action_id must not be empty")
    state = state.strip().lower()
    if state == "unread":
        clear_action_state(action_id)
        return {"action_id": action_id, "state": "unread", "snoozed_until": None}
    if state not in ACTION_STATES:
        raise ValueError(f"state must be one of {sorted(ACTION_STATES | {'unread'})}")
    normalised_until = _normalise_until(snoozed_until)
    if state == "snoozed":
        if not normalised_until:
            raise ValueError("snoozed_until is required for snoozed state")
        until = datetime.fromisoformat(normalised_until)
        if until <= datetime.now(timezone.utc):
            raise ValueError("snoozed_until must be in the future")
    else:
        normalised_until = None
    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO action_states (action_id, state, snoozed_until, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(action_id) DO UPDATE SET
                 state=excluded.state,
                 snoozed_until=excluded.snoozed_until,
                 updated_at=excluded.updated_at""",
            (action_id, state, normalised_until, now, now),
        )
        conn.commit()
    return {"action_id": action_id, "state": state, "snoozed_until": normalised_until}


def clear_action_state(action_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM action_states WHERE action_id = ?", (action_id.strip(),))
        conn.commit()


def list_action_states() -> dict[str, dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT action_id, state, snoozed_until, updated_at FROM action_states"
        ).fetchall()
    return {
        row[0]: {
            "state": row[1],
            "snoozed_until": row[2],
            "updated_at": row[3],
        }
        for row in rows
    }
