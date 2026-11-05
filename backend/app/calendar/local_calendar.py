from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from backend.app.storage.db import get_db_connection


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name} format. Use ISO 8601 (e.g. 2026-07-03T10:00:00).") from exc


def _event_row(row: tuple[Any, ...]) -> dict[str, Any]:
    event = {
        "uid": row[0],
        "summary": row[1],
        "start": row[2],
        "end": row[3],
        "description": row[4] or "",
    }
    if len(row) > 5 and row[5]:
        event["all_day"] = True
    if len(row) > 6 and row[6]:
        event["recurrence"] = row[6]
    if len(row) > 7 and row[7]:
        event["recurrence_until"] = row[7]
    if len(row) > 8 and row[8] is not None:
        event["reminder_minutes"] = row[8]
    return event


def _aligned_pair(left: datetime, right: datetime) -> tuple[datetime, datetime]:
    """Compare naive local values and timezone-aware query values safely."""
    if left.tzinfo is None and right.tzinfo is not None:
        left = left.replace(tzinfo=right.tzinfo)
    elif left.tzinfo is not None and right.tzinfo is None:
        right = right.replace(tzinfo=left.tzinfo)
    if left.tzinfo is not None and right.tzinfo is not None:
        return left.astimezone(timezone.utc), right.astimezone(timezone.utc)
    return left, right


def _overlaps(event_start: datetime, event_end: datetime, range_start: datetime, range_end: datetime) -> bool:
    event_start, range_end = _aligned_pair(event_start, range_end)
    event_end, range_start = _aligned_pair(event_end, range_start)
    return event_start < range_end and event_end > range_start


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _add_years(value: datetime, years: int) -> datetime:
    year = value.year + years
    day = min(value.day, monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def _advance(value: datetime, recurrence: str) -> datetime:
    if recurrence == "daily":
        return value + timedelta(days=1)
    if recurrence == "weekly":
        return value + timedelta(days=7)
    if recurrence == "monthly":
        return _add_months(value, 1)
    if recurrence == "yearly":
        return _add_years(value, 1)
    return value


def _recurrence_until(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid recurrence_until format. Use YYYY-MM-DD.") from exc


def _expanded_events(
    row: tuple[Any, ...],
    range_start: datetime,
    range_end: datetime,
) -> list[dict[str, Any]]:
    base = _event_row(row)
    base_start = _parse_datetime(row[2], "start_datetime")
    base_end = _parse_datetime(row[3], "end_datetime")
    duration = base_end - base_start
    recurrence = str(row[6] or "none").lower()
    if recurrence not in {"none", "daily", "weekly", "monthly", "yearly"}:
        recurrence = "none"
    until = _recurrence_until(row[7])

    occurrences: list[dict[str, Any]] = []
    occurrence_start = base_start
    for _ in range(10000):
        if until and occurrence_start.date() > until:
            break
        occurrence_end = occurrence_start + duration
        if _overlaps(occurrence_start, occurrence_end, range_start, range_end):
            occurrence = dict(base)
            occurrence["start"] = occurrence_start.isoformat()
            occurrence["end"] = occurrence_end.isoformat()
            occurrences.append(occurrence)
        comparable_start, comparable_end = _aligned_pair(occurrence_start, range_end)
        if recurrence == "none" or comparable_start >= comparable_end:
            break
        next_start = _advance(occurrence_start, recurrence)
        if next_start <= occurrence_start:
            break
        occurrence_start = next_start
    return occurrences


def list_events(start_date: str, end_date: str) -> list[dict[str, Any]]:
    start = _parse_datetime(start_date, "start_date")
    end = _parse_datetime(end_date, "end_date")
    if end <= start:
        raise ValueError("end_date must be later than start_date.")

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT uid, title, start_datetime, end_datetime, description,
                   all_day, recurrence, recurrence_until, reminder_minutes
            FROM calendar_events
            ORDER BY start_datetime ASC
            """
        ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        events.extend(_expanded_events(row, start, end))
    return sorted(events, key=lambda item: item["start"])


def search_events(query: str) -> list[dict[str, Any]]:
    term = query.strip()
    if not term:
        return []
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT uid, title, start_datetime, end_datetime, description,
                      all_day, recurrence, recurrence_until, reminder_minutes
               FROM calendar_events
               WHERE title LIKE ? OR description LIKE ?
               ORDER BY start_datetime ASC""",
            (f"%{term}%", f"%{term}%"),
        ).fetchall()
    return [_event_row(row) for row in rows]


def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str | None = None,
    description: str | None = None,
    all_day: bool = False,
    recurrence: str | None = None,
    recurrence_until: str | None = None,
    reminder_minutes: int | None = None,
) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise ValueError("Event title must not be empty.")

    start = _parse_datetime(start_datetime, "start_datetime")
    if all_day:
        end = _parse_datetime(end_datetime, "end_datetime") + timedelta(days=1) if end_datetime else start + timedelta(days=1)
    else:
        end = _parse_datetime(end_datetime, "end_datetime") if end_datetime else start + timedelta(hours=1)
    if end <= start:
        raise ValueError("end_datetime must be later than start_datetime.")

    uid = f"local-{uuid4()}"
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO calendar_events
                (uid, title, start_datetime, end_datetime, description,
                 all_day, recurrence, recurrence_until, reminder_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, title, start.isoformat(), end.isoformat(), description or "",
             int(all_day), recurrence, recurrence_until, reminder_minutes),
        )
        conn.commit()

    return {
        "status": "created",
        "uid": uid,
        "summary": title,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "description": description or "",
        "all_day": all_day,
        "recurrence": recurrence,
        "recurrence_until": recurrence_until,
        "reminder_minutes": reminder_minutes,
    }


def modify_event(uid: str, updated_fields: dict[str, str]) -> dict[str, Any]:
    if not updated_fields:
        raise ValueError("At least one event field must be provided.")

    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT uid, title, start_datetime, end_datetime, description,
                    all_day, recurrence, recurrence_until, reminder_minutes
             FROM calendar_events WHERE uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            raise KeyError(f"Event '{uid}' not found.")

        current = _event_row(row)
        title = updated_fields.get("title", current["summary"]).strip()
        start_value = updated_fields.get("start_datetime", current["start"])
        end_value = updated_fields.get("end_datetime", current["end"])
        all_day = bool(updated_fields.get("all_day", current.get("all_day", False)))
        start = _parse_datetime(start_value, "start_datetime")
        if all_day:
            end = _parse_datetime(end_value, "end_datetime")
            if not (current.get("all_day") and "end_datetime" not in updated_fields):
                end += timedelta(days=1)
        else:
            end = _parse_datetime(end_value, "end_datetime")
        if not title:
            raise ValueError("Event title must not be empty.")
        if end <= start:
            raise ValueError("end_datetime must be later than start_datetime.")

        description = updated_fields.get("description", current["description"])
        recurrence = updated_fields.get("recurrence", current.get("recurrence"))
        recurrence_until = updated_fields.get("recurrence_until", current.get("recurrence_until"))
        reminder_minutes = updated_fields.get("reminder_minutes", current.get("reminder_minutes"))
        conn.execute(
            """
            UPDATE calendar_events
            SET title = ?, start_datetime = ?, end_datetime = ?, description = ?,
                all_day = ?, recurrence = ?, recurrence_until = ?, reminder_minutes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE uid = ?
            """,
            (title, start.isoformat(), end.isoformat(), description, int(all_day),
             recurrence, recurrence_until, reminder_minutes, uid),
        )
        conn.commit()

    return {
        "status": "modified",
        "uid": uid,
        "summary": title,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "description": description or "",
        "all_day": all_day,
        "recurrence": recurrence,
        "recurrence_until": recurrence_until,
        "reminder_minutes": reminder_minutes,
    }


def delete_event(uid: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT uid, title, start_datetime, end_datetime, description,
                    all_day, recurrence, recurrence_until, reminder_minutes
             FROM calendar_events WHERE uid = ?""",
            (uid,),
        ).fetchone()
        if not row:
            raise KeyError(f"Event '{uid}' not found.")
        event = _event_row(row)
        conn.execute("DELETE FROM calendar_events WHERE uid = ?", (uid,))
        conn.commit()

    return {"status": "deleted", **event}
