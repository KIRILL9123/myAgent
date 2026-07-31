import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from backend.app.storage.db import get_db_connection

STATUSES = {"PROPOSED", "ACTIVE", "CANCELLED", "EXPIRED"}
SUBSCRIPTION_TYPES = {"TRIAL", "PAID", "UNKNOWN"}
SOURCE_TYPES = {"MANUAL", "EMAIL"}
TERMINAL_STATUSES = {"CANCELLED", "EXPIRED"}


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
        "id", "name", "provider", "description", "status", "subscription_type",
        "amount", "currency", "billing_cycle", "trial_ends_at", "next_charge_at",
        "reminder_at", "reminder_sent_at", "cancellation_url",
        "cancellation_instructions", "confidence", "provenance", "source_type",
        "source_ref", "created_at", "updated_at", "activated_at", "cancelled_at",
        "expired_at", "approval_provenance",
    )
    result = dict(zip(keys, row))
    result["provenance"] = _loads(result.get("provenance"), {})
    result["approval_provenance"] = _loads(result.get("approval_provenance"), None)
    return result


_SELECT = """SELECT id, name, provider, description, status, subscription_type,
                     amount, currency, billing_cycle, trial_ends_at, next_charge_at,
                     reminder_at, reminder_sent_at, cancellation_url,
                     cancellation_instructions, confidence, provenance_json, source_type,
                     source_ref, created_at, updated_at, activated_at, cancelled_at,
                     expired_at, approval_provenance_json
              FROM subscriptions"""


def _get(subscription_id: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(f"{_SELECT} WHERE id = ?", (subscription_id,)).fetchone()
    return _row_to_dict(row) if row else None


def _record_event(conn, subscription_id: str, event_type: str,
                  from_status: str | None, to_status: str | None,
                  payload: dict[str, Any] | None = None) -> None:
    conn.execute(
        """INSERT INTO subscription_events
           (subscription_id, event_type, from_status, to_status, payload_json)
           VALUES (?, ?, ?, ?, ?)""",
        (subscription_id, event_type, from_status, to_status, _json(payload, {})),
    )


def _default_reminder_at(event_at: str | None) -> str | None:
    if not event_at:
        return None
    lead_days = max(1, int(os.getenv("SUBSCRIPTION_REMINDER_LEAD_DAYS", "7")))
    event = datetime.fromisoformat(event_at)
    return (event - timedelta(days=lead_days)).isoformat()


def _validate_schedule(trial_ends_at: str | None, next_charge_at: str | None,
                       reminder_at: str | None) -> None:
    charge_or_trial = next_charge_at or trial_ends_at
    if charge_or_trial and reminder_at and reminder_at > charge_or_trial:
        raise ValueError("reminder_at must be before the trial end or next charge")


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    candidate = str(value).strip()
    parsed = urlparse(candidate)
    if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
        return candidate
    return None


def create_subscription(
    name: str,
    provider: str | None = None,
    description: str | None = None,
    subscription_type: str = "UNKNOWN",
    amount: float | None = None,
    currency: str | None = None,
    billing_cycle: str | None = None,
    trial_ends_at: str | None = None,
    next_charge_at: str | None = None,
    reminder_at: str | None = None,
    cancellation_url: str | None = None,
    cancellation_instructions: str | None = None,
    source_type: str = "MANUAL",
    source_ref: str | None = None,
    confidence: float = 1.0,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    name = name.strip()
    source_type = source_type.upper()
    subscription_type = subscription_type.upper()
    if not name:
        raise ValueError("name must not be empty")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"source_type must be one of {sorted(SOURCE_TYPES)}")
    if subscription_type not in SUBSCRIPTION_TYPES:
        raise ValueError(f"subscription_type must be one of {sorted(SUBSCRIPTION_TYPES)}")
    if amount is not None and amount < 0:
        raise ValueError("amount must not be negative")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    trial_ends_at = _validate_datetime(trial_ends_at, "trial_ends_at")
    next_charge_at = _validate_datetime(next_charge_at, "next_charge_at")
    reminder_at = _validate_datetime(reminder_at, "reminder_at")
    if reminder_at is None:
        reminder_at = _default_reminder_at(next_charge_at or trial_ends_at)
    _validate_schedule(trial_ends_at, next_charge_at, reminder_at)
    cancellation_url = _safe_url(cancellation_url)

    subscription_id = str(uuid.uuid4())
    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (id, name, provider, description, subscription_type, amount, currency,
                billing_cycle, trial_ends_at, next_charge_at, reminder_at,
                cancellation_url, cancellation_instructions, confidence,
                provenance_json, source_type, source_ref, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (subscription_id, name, provider, description, subscription_type, amount,
             currency, billing_cycle, trial_ends_at, next_charge_at, reminder_at,
             cancellation_url, cancellation_instructions, confidence,
             _json(provenance, {}), source_type, source_ref, now, now),
        )
        _record_event(conn, subscription_id, "CREATED", None, "PROPOSED", {
            "source_type": source_type, "source_ref": source_ref,
        })
        conn.commit()
    return _get(subscription_id)  # type: ignore[return-value]


def get_subscription(subscription_id: str) -> dict[str, Any] | None:
    return _get(subscription_id)


def list_subscriptions(status: str | None = None) -> list[dict[str, Any]]:
    if status and status.upper() not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status.upper())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as conn:
        rows = conn.execute(
            f"{_SELECT}{where} ORDER BY CASE WHEN next_charge_at IS NULL THEN 1 ELSE 0 END, next_charge_at, created_at",
            params,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_subscriptions_by_source_prefix(prefix: str) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(f"{_SELECT} WHERE source_ref LIKE ? ORDER BY created_at", (f"{prefix}%",)).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_due_reminders(now: str | None = None) -> list[dict[str, Any]]:
    cutoff = _validate_datetime(now, "now") if now else _now()
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""{_SELECT}
                WHERE status = 'ACTIVE' AND reminder_at IS NOT NULL
                  AND reminder_at <= ? AND reminder_sent_at IS NULL
                ORDER BY reminder_at""",
            (cutoff,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def mark_reminder_sent(subscription_id: str, sent_at: str | None = None) -> None:
    subscription = _get(subscription_id)
    if not subscription:
        raise KeyError("subscription not found")
    sent_at = _validate_datetime(sent_at, "sent_at") if sent_at else _now()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE subscriptions SET reminder_sent_at = ?, updated_at = ? WHERE id = ?",
            (sent_at, sent_at, subscription_id),
        )
        _record_event(conn, subscription_id, "REMINDER_SENT", "ACTIVE", "ACTIVE", {"sent_at": sent_at})
        conn.commit()


def update_subscription(subscription_id: str, **changes: Any) -> dict[str, Any]:
    subscription = _get(subscription_id)
    if not subscription:
        raise KeyError("subscription not found")
    if subscription["status"] in TERMINAL_STATUSES:
        raise ValueError("terminal subscriptions cannot be edited")
    allowed = {
        "name", "provider", "description", "subscription_type", "amount", "currency",
        "billing_cycle", "trial_ends_at", "next_charge_at", "reminder_at",
        "cancellation_url", "cancellation_instructions", "confidence",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unsupported fields: {sorted(unknown)}")
    if "name" in changes:
        changes["name"] = str(changes["name"]).strip()
        if not changes["name"]:
            raise ValueError("name must not be empty")
    if "subscription_type" in changes:
        changes["subscription_type"] = str(changes["subscription_type"]).upper()
        if changes["subscription_type"] not in SUBSCRIPTION_TYPES:
            raise ValueError(f"subscription_type must be one of {sorted(SUBSCRIPTION_TYPES)}")
    for field in ("trial_ends_at", "next_charge_at", "reminder_at"):
        if field in changes:
            changes[field] = _validate_datetime(changes[field], field)
    if "confidence" in changes and not 0.0 <= changes["confidence"] <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    if "cancellation_url" in changes:
        changes["cancellation_url"] = _safe_url(changes["cancellation_url"])
    trial = changes.get("trial_ends_at", subscription["trial_ends_at"])
    charge = changes.get("next_charge_at", subscription["next_charge_at"])
    reminder = changes.get("reminder_at", subscription["reminder_at"])
    _validate_schedule(trial, charge, reminder)
    if not changes:
        return subscription
    assignments = ", ".join(f"{key} = ?" for key in changes)
    now = _now()
    with get_db_connection() as conn:
        conn.execute(f"UPDATE subscriptions SET {assignments}, updated_at = ? WHERE id = ?",
                     [*changes.values(), now, subscription_id])
        _record_event(conn, subscription_id, "UPDATED", subscription["status"], subscription["status"],
                      {"fields": sorted(changes)})
        conn.commit()
    return _get(subscription_id)  # type: ignore[return-value]


def transition_subscription(subscription_id: str, action: str,
                             approval_provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    subscription = _get(subscription_id)
    if not subscription:
        raise KeyError("subscription not found")
    current = subscription["status"]
    transitions = {
        "approve": ("ACTIVE", {"PROPOSED"}),
        "cancel": ("CANCELLED", {"PROPOSED", "ACTIVE", "EXPIRED"}),
        "reopen": ("ACTIVE", {"EXPIRED"}),
        "expire": ("EXPIRED", {"ACTIVE"}),
    }
    if action not in transitions:
        raise ValueError(f"unsupported action: {action}")
    target, allowed = transitions[action]
    if current not in allowed:
        raise ValueError(f"cannot {action} subscription in {current} status")
    now = _now()
    timestamp_field = {"ACTIVE": "activated_at", "CANCELLED": "cancelled_at", "EXPIRED": "expired_at"}[target]
    fields = ["status = ?", "updated_at = ?", f"{timestamp_field} = ?"]
    values: list[Any] = [target, now, now]
    if action == "approve":
        fields.append("approval_provenance_json = ?")
        values.append(_json(approval_provenance, {}))
    values.append(subscription_id)
    with get_db_connection() as conn:
        conn.execute(f"UPDATE subscriptions SET {', '.join(fields)} WHERE id = ?", values)
        _record_event(conn, subscription_id, action.upper(), current, target,
                      {"approval_provenance": approval_provenance} if approval_provenance else None)
        conn.commit()
    return _get(subscription_id)  # type: ignore[return-value]


def expire_overdue(now: str | None = None) -> list[dict[str, Any]]:
    cutoff = _validate_datetime(now, "now") if now else _now()
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM subscriptions WHERE status = 'ACTIVE' AND trial_ends_at IS NOT NULL AND trial_ends_at < ?",
            (cutoff,),
        ).fetchall()
    return [transition_subscription(row[0], "expire") for row in rows]


def get_subscription_events(subscription_id: str) -> list[dict[str, Any]]:
    if not _get(subscription_id):
        raise KeyError("subscription not found")
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, event_type, from_status, to_status, payload_json, created_at FROM subscription_events WHERE subscription_id = ? ORDER BY id",
            (subscription_id,),
        ).fetchall()
    return [{"id": row[0], "event_type": row[1], "from_status": row[2], "to_status": row[3],
             "payload": _loads(row[4], {}), "created_at": row[5]} for row in rows]
