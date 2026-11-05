"""Policy and coalescing layer for proactive notifications."""

import json
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from backend.app.action_center_service import build_action_center
from backend.app.notifications.telegram_notifier import send_notification
from backend.app.storage.db import get_db_connection
from backend.app.temporal.time_context import DEFAULT_TIMEZONE, build_temporal_context, parse_datetime

PRIORITIES = {"critical", "high", "medium", "low"}
DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "timezone": DEFAULT_TIMEZONE,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    "max_messages_per_window": 3,
    "window_minutes": 60,
    "min_priority": "medium",
    "coalesce_window_minutes": 15,
}


def _now() -> datetime:
    return build_temporal_context().now_utc


def _parse_time(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
    except (AttributeError, ValueError) as exc:
        raise ValueError("quiet hours must use HH:MM") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("quiet hours must use HH:MM")
    return hour * 60 + minute


def _validate_preferences(changes: dict[str, Any]) -> dict[str, Any]:
    result = dict(changes)
    if "timezone" in result:
        try:
            ZoneInfo(str(result["timezone"]))
        except Exception as exc:
            raise ValueError("invalid notification timezone") from exc
    for key in ("quiet_hours_start", "quiet_hours_end"):
        if key in result:
            _parse_time(str(result[key]))
    for key in ("max_messages_per_window", "window_minutes", "coalesce_window_minutes"):
        if key in result:
            result[key] = int(result[key])
    if "max_messages_per_window" in result and not 1 <= result["max_messages_per_window"] <= 50:
        raise ValueError("max_messages_per_window must be between 1 and 50")
    if "window_minutes" in result and not 5 <= result["window_minutes"] <= 1440:
        raise ValueError("window_minutes must be between 5 and 1440")
    if "coalesce_window_minutes" in result and not 1 <= result["coalesce_window_minutes"] <= 1440:
        raise ValueError("coalesce_window_minutes must be between 1 and 1440")
    if "min_priority" in result and result["min_priority"] not in PRIORITIES:
        raise ValueError(f"min_priority must be one of {sorted(PRIORITIES)}")
    if "enabled" in result:
        result["enabled"] = bool(result["enabled"])
    return result


def get_notification_preferences() -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT enabled, timezone, quiet_hours_start, quiet_hours_end,
                      max_messages_per_window, window_minutes, min_priority,
                      coalesce_window_minutes, updated_at
               FROM notification_preferences WHERE id = 1"""
        ).fetchone()
    if not row:
        return dict(DEFAULTS)
    keys = (*DEFAULTS.keys(), "updated_at")
    result = dict(zip(keys, row))
    result["enabled"] = bool(result["enabled"])
    return result


def update_notification_preferences(**changes: Any) -> dict[str, Any]:
    clean = _validate_preferences({key: value for key, value in changes.items() if value is not None})
    if not clean:
        return get_notification_preferences()
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = [clean[key] for key in clean]
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE notification_preferences SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            values,
        )
        conn.commit()
    return get_notification_preferences()


def _in_quiet_hours(now: datetime, preferences: dict[str, Any]) -> bool:
    local_now = now.astimezone(ZoneInfo(preferences["timezone"]))
    current = local_now.hour * 60 + local_now.minute
    start = _parse_time(preferences["quiet_hours_start"])
    end = _parse_time(preferences["quiet_hours_end"])
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 4)


def _already_sent(dedupe_key: str, now: datetime, window_hours: int = 24) -> bool:
    cutoff = (now - timedelta(hours=window_hours)).isoformat()
    with get_db_connection() as conn:
        return bool(conn.execute(
            """SELECT 1 FROM notification_deliveries
               WHERE channel = 'telegram' AND recipient = 'default'
                 AND dedupe_key = ? AND status = 'sent' AND sent_at >= ?
               LIMIT 1""",
            (dedupe_key, cutoff),
        ).fetchone())


def _sent_in_window(now: datetime, minutes: int) -> int:
    cutoff = (now - timedelta(minutes=minutes)).isoformat()
    with get_db_connection() as conn:
        return conn.execute(
            """SELECT COUNT(*) FROM notification_deliveries
               WHERE channel = 'telegram' AND recipient = 'default'
                 AND status = 'sent' AND sent_at >= ?""",
            (cutoff,),
        ).fetchone()[0]


def _record(status: str, action_ids: list[str], priority: str, *, dedupe_key: str, reason: str | None = None, sent_at: datetime | None = None) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO notification_deliveries
               (channel, recipient, dedupe_key, action_ids_json, priority, status, reason, sent_at)
               VALUES ('telegram', 'default', ?, ?, ?, ?, ?, ?)""",
            (dedupe_key, json.dumps(action_ids, ensure_ascii=False), priority, status, reason,
             (sent_at or _now()).isoformat()),
        )
        conn.commit()


def _format_message(actions: list[dict[str, Any]]) -> str:
    lines = ["🔔 Mira — требует внимания", ""]
    for action in actions:
        marker = "🚨" if action["priority"] == "critical" else "•"
        due = f" · срок: {action['due_at']}" if action.get("due_at") else ""
        lines.append(f"{marker} {action['title']}{due}")
        if action.get("summary"):
            lines.append(f"  {action['summary']}")
    return "\n".join(lines)[:3900]


async def deliver_action_notifications(reference_time: datetime | None = None) -> dict[str, Any]:
    preferences = get_notification_preferences()
    context = build_temporal_context(reference_time, preferences["timezone"])
    now = context.now_utc
    if not preferences["enabled"]:
        return {"status": "suppressed", "reason": "disabled", "action_ids": []}

    center = build_action_center(temporal_context=context, mode="attention", limit=100, include_external=False)
    minimum_rank = _priority_rank(preferences["min_priority"])
    candidates = [
        item for item in center["actions"]
        if (item.get("reminder_due") or item.get("priority") == "critical" or item.get("requires_approval"))
        and (item.get("priority") == "critical" or _priority_rank(item["priority"]) <= minimum_rank)
    ]
    fresh: list[dict[str, Any]] = []
    for item in candidates:
        dedupe_key = f"{item['id']}:{item['status']}:{item['priority']}"
        if not _already_sent(dedupe_key, now):
            fresh.append({**item, "_dedupe_key": dedupe_key})
    if not fresh:
        return {"status": "idle", "reason": "nothing_new", "action_ids": []}

    fresh.sort(key=lambda item: _priority_rank(item["priority"]))
    has_critical = any(item["priority"] == "critical" for item in fresh)
    if _in_quiet_hours(now, preferences) and not has_critical:
        return {"status": "suppressed", "reason": "quiet_hours", "action_ids": [item["id"] for item in fresh]}
    if _sent_in_window(now, preferences["window_minutes"]) >= preferences["max_messages_per_window"] and not has_critical:
        return {"status": "suppressed", "reason": "notification_budget", "action_ids": [item["id"] for item in fresh]}

    action_ids = [item["id"] for item in fresh]
    priority = fresh[0]["priority"]
    result = await send_notification(_format_message(fresh))
    if isinstance(result, dict) and result.get("status") == "dry_run":
        _record("dry_run", action_ids, priority, dedupe_key=f"batch:{now.isoformat()}", reason="execution_mode")
        return {"status": "dry_run", "action_ids": action_ids, "message": result["would_do"]["message"]}
    if result is not True:
        _record("failed", action_ids, priority, dedupe_key=f"batch:{now.isoformat()}", reason="telegram_send_failed")
        return {"status": "failed", "reason": "telegram_send_failed", "action_ids": action_ids}

    for item in fresh:
        _record("sent", [item["id"]], item["priority"], dedupe_key=item["_dedupe_key"], sent_at=now)
        if item.get("reminder_due"):
            try:
                if item["kind"] == "commitment":
                    from backend.app.commitments.commitment_service import mark_reminder_sent
                    mark_reminder_sent(item["source_id"], now.isoformat())
                elif item["kind"] == "subscription":
                    from backend.app.subscriptions.subscription_service import mark_reminder_sent
                    mark_reminder_sent(item["source_id"], now.isoformat())
            except (KeyError, ValueError):
                pass
    return {"status": "sent", "action_ids": action_ids, "coalesced": len(action_ids) > 1}


async def deliver_calendar_reminders(reference_time: datetime | None = None) -> dict[str, Any]:
    """Send due calendar reminders to Telegram with quiet hours and deduplication."""
    preferences = get_notification_preferences()
    context = build_temporal_context(reference_time, preferences["timezone"])
    now = context.now_utc
    if not preferences["enabled"]:
        return {"status": "suppressed", "reason": "disabled", "event_ids": []}

    local_now = context.now_local
    query_start = local_now.replace(second=0, microsecond=0)
    query_end = query_start + timedelta(days=2)
    try:
        from backend.app.calendar.calendar_service import list_events
        import asyncio
        events = await asyncio.to_thread(list_events, query_start.isoformat(), query_end.isoformat())
    except Exception:
        return {"status": "idle", "reason": "calendar_unavailable", "event_ids": []}
    if not isinstance(events, list):
        return {"status": "idle", "reason": "calendar_unavailable", "event_ids": []}

    due: list[dict[str, Any]] = []
    for event in events:
        reminder = event.get("reminder_minutes")
        if reminder is None:
            continue
        try:
            event_start = parse_datetime(event.get("start"), default_timezone=context.zone)
            if event_start is None:
                continue
            due_at = event_start - timedelta(minutes=int(reminder))
            if not due_at <= now < due_at + timedelta(minutes=preferences["coalesce_window_minutes"]):
                continue
        except (TypeError, ValueError):
            continue
        dedupe_key = f"calendar:{event.get('uid', '')}:{event.get('start', '')}"
        if not event.get("uid") or _already_sent(dedupe_key, now):
            continue
        due.append({**event, "_dedupe_key": dedupe_key})

    if not due:
        return {"status": "idle", "reason": "nothing_new", "event_ids": []}
    if _in_quiet_hours(now, preferences):
        return {"status": "suppressed", "reason": "quiet_hours", "event_ids": [event["uid"] for event in due]}

    lines = ["🔔 Mira — напоминание о календаре", ""]
    deliverable = due[: preferences["max_messages_per_window"]]
    for event in deliverable:
        start = str(event.get("start", ""))
        lines.append(f"• {event.get('summary', 'Событие')} · {start.replace('T', ' ')}")
    result = await send_notification("\n".join(lines))
    due_event_ids = [event["uid"] for event in due]
    if isinstance(result, dict) and result.get("status") == "dry_run":
        _record("dry_run", due_event_ids, "medium", dedupe_key=f"calendar-batch:{now.isoformat()}", reason="execution_mode")
        return {"status": "dry_run", "event_ids": due_event_ids}
    if result is not True:
        _record("failed", due_event_ids, "medium", dedupe_key=f"calendar-batch:{now.isoformat()}", reason="telegram_send_failed")
        return {"status": "failed", "event_ids": due_event_ids}
    event_ids = [event["uid"] for event in deliverable]
    for event in deliverable:
        _record("sent", [event["uid"]], "medium", dedupe_key=event["_dedupe_key"], sent_at=now)
    return {"status": "sent", "event_ids": event_ids}
