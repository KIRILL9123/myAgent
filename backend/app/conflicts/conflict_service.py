"""Read-only conflict detection across Calendar and Commitments.

The service deliberately returns a projection instead of writing conflict rows.
Calendar events and commitments remain the source of truth; Today, Action
Center, Calendar and the assistant can consume the same deterministic result.
"""

from __future__ import annotations

from datetime import datetime, timedelta, time
from typing import Any

from backend.app.calendar.calendar_service import list_events, use_local_calendar
from backend.app.commitments.commitment_service import list_commitments
from backend.app.conflicts.preference_conflict_service import (
    detect_preference_conflicts,
    extract_calendar_preferences,
)
from backend.app.temporal.time_context import TemporalContext, build_temporal_context


def _event_interval(event: dict[str, Any], context: TemporalContext) -> tuple[datetime, datetime] | None:
    start = context.parse(event.get("start"), assume_local=True)
    end = context.parse(event.get("end"), assume_local=True)
    if not start:
        return None
    if not end or end <= start:
        end = start + timedelta(hours=1)
    return start, end


def _event_key(event: dict[str, Any], start: datetime) -> str:
    return f"{event.get('uid', '')}:{start.isoformat()}"


def _conflict(
    *,
    conflict_id: str,
    conflict_type: str,
    title: str,
    summary: str,
    priority: str,
    event: dict[str, Any],
    event_start: datetime,
    event_end: datetime,
    commitment: dict[str, Any] | None = None,
    due_at: str | None = None,
    related_event: dict[str, Any] | None = None,
    related_event_start: datetime | None = None,
    related_event_end: datetime | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": conflict_id,
        "type": conflict_type,
        "title": title,
        "summary": summary,
        "priority": priority,
        "status": "conflict",
        "event_uid": event.get("uid"),
        "event_title": event.get("summary", ""),
        "event_start": event_start.isoformat(),
        "event_end": event_end.isoformat(),
        "due_at": due_at,
        "commitment_id": commitment.get("id") if commitment else None,
        "commitment_title": commitment.get("title") if commitment else None,
        "related_event_uid": related_event.get("uid") if related_event else None,
        "related_event_title": related_event.get("summary") if related_event else None,
        "related_event_start": related_event_start.isoformat() if related_event_start else None,
        "related_event_end": related_event_end.isoformat() if related_event_end else None,
        "target": "/calendar",
    }
    return result


def detect_conflicts(
    reference_time: datetime | None = None,
    *,
    timezone_name: str | None = None,
    temporal_context: TemporalContext | None = None,
    horizon_days: int = 30,
    include_external: bool = True,
    events: list[dict[str, Any]] | None = None,
    commitments: list[dict[str, Any]] | None = None,
    preference_facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return calendar/commitment conflicts for the next horizon.

    v1 detects two concrete conflicts:
    - an active commitment deadline falls inside a calendar event;
    - two different calendar events overlap.

    External calendar reads are skipped when ``include_external`` is false,
    while the local calendar remains available for the local-first dashboard.
    """
    if temporal_context is not None and reference_time is not None:
        raise ValueError("provide either reference_time or temporal_context")
    context = temporal_context or build_temporal_context(reference_time, timezone_name)
    horizon_days = max(1, min(int(horizon_days), 365))

    start_local = datetime.combine(context.today, time.min, tzinfo=context.zone)
    end_local = start_local + timedelta(days=horizon_days + 1)
    provided_events = events is not None
    if events is None:
        if not include_external and not use_local_calendar():
            return {
                "status": "not_requested",
                "generated_at": context.now_utc.isoformat(),
                "timezone": context.timezone_name,
                "today": context.today.isoformat(),
                "horizon_days": horizon_days,
                "conflicts": [],
                "events_checked": 0,
                "commitments_checked": 0,
            }
        try:
            loaded_events = list_events(start_local.isoformat(), end_local.isoformat())
        except Exception as exc:
            return {
                "status": "error",
                "generated_at": context.now_utc.isoformat(),
                "timezone": context.timezone_name,
                "today": context.today.isoformat(),
                "horizon_days": horizon_days,
                "conflicts": [],
                "events_checked": 0,
                "commitments_checked": 0,
                "error": str(exc),
            }
        if not isinstance(loaded_events, list):
            return {
                "status": "error",
                "generated_at": context.now_utc.isoformat(),
                "timezone": context.timezone_name,
                "today": context.today.isoformat(),
                "horizon_days": horizon_days,
                "conflicts": [],
                "events_checked": 0,
                "commitments_checked": 0,
                "error": "calendar returned an invalid response",
            }
        events = loaded_events
    if commitments is None:
        commitments = [item for item in list_commitments(include_completed=False) if item.get("status") == "ACTIVE"]

    intervals: list[tuple[dict[str, Any], datetime, datetime, str]] = []
    for event in events:
        interval = _event_interval(event, context)
        if not interval:
            continue
        event_start, event_end = interval
        if event_end <= context.now_utc - timedelta(days=1) or (not provided_events and event_start >= end_local.astimezone(event_start.tzinfo)):
            continue
        intervals.append((event, event_start, event_end, _event_key(event, event_start)))

    conflicts: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, (event, event_start, event_end, event_key) in enumerate(intervals):
        linked_event_ids = {str(value) for value in (event.get("commitment_ids") or [])}
        for commitment in commitments:
            commitment_id = str(commitment.get("id", ""))
            if not commitment_id or event.get("uid") in {str(value) for value in (commitment.get("related_calendar_event_ids") or [])}:
                continue
            deadline = context.parse(commitment.get("deadline_at"))
            if not deadline or deadline < context.now_utc - timedelta(days=1):
                continue
            if event_start <= deadline < event_end:
                conflict_id = f"event-commitment:{event.get('uid')}:{commitment_id}:{event_start.isoformat()}"
                if conflict_id in seen:
                    continue
                seen.add(conflict_id)
                priority = "critical" if deadline < context.now_utc else "high"
                conflicts.append(_conflict(
                    conflict_id=conflict_id,
                    conflict_type="event_commitment",
                    title=f"Конфликт расписания: {event.get('summary', 'Событие')} и {commitment.get('title', 'обязательство')}",
                    summary=f"Срок обязательства «{commitment.get('title', 'без названия')}» попадает внутрь события «{event.get('summary', 'без названия')}».",
                    priority=priority,
                    event=event,
                    event_start=event_start,
                    event_end=event_end,
                    commitment=commitment,
                    due_at=commitment.get("deadline_at"),
                ))

        for other_event, other_start, other_end, other_key in intervals[index + 1:]:
            if str(event.get("uid")) == str(other_event.get("uid")):
                continue
            if event_start >= other_end or other_start >= event_end:
                continue
            pair = sorted((event_key, other_key))
            conflict_id = f"event-overlap:{pair[0]}:{pair[1]}"
            if conflict_id in seen:
                continue
            seen.add(conflict_id)
            conflicts.append(_conflict(
                conflict_id=conflict_id,
                conflict_type="event_overlap",
                title=f"Пересечение событий: {event.get('summary', 'Событие')} и {other_event.get('summary', 'событие')}",
                summary=f"События «{event.get('summary', 'без названия')}» и «{other_event.get('summary', 'без названия')}» идут одновременно.",
                priority="high",
                event=event,
                event_start=event_start,
                event_end=event_end,
                related_event=other_event,
                related_event_start=other_start,
                related_event_end=other_end,
                due_at=event.get("start"),
            ))

    preference_rules = extract_calendar_preferences(preference_facts)
    conflicts.extend(detect_preference_conflicts([item[0] for item in intervals], context, preferences=preference_rules))

    conflicts.sort(key=lambda item: (0 if item["priority"] == "critical" else 1, item.get("due_at") or "9999", item["id"]))
    return {
        "status": "ok",
        "generated_at": context.now_utc.isoformat(),
        "timezone": context.timezone_name,
        "today": context.today.isoformat(),
        "horizon_days": horizon_days,
        "conflicts": conflicts,
        "events_checked": len(intervals),
        "commitments_checked": len(commitments),
        "preferences_checked": len(preference_rules),
    }


def preview_event_conflicts(
    *,
    title: str,
    start_datetime: str,
    end_datetime: str | None = None,
    all_day: bool = False,
    exclude_uid: str | None = None,
    timezone_name: str | None = None,
    existing_events: list[dict[str, Any]] | None = None,
    all_day_end_is_exclusive: bool = False,
) -> list[dict[str, Any]]:
    """Check a draft event before saving it, without mutating Calendar or Memory."""
    context = build_temporal_context(timezone_name=timezone_name)
    start = context.parse(start_datetime, assume_local=True)
    if not start:
        raise ValueError("Invalid start_datetime format.")
    if all_day:
        end = context.parse(end_datetime, assume_local=True) if end_datetime else None
        if end and not all_day_end_is_exclusive:
            end += timedelta(days=1)
        end = end or start + timedelta(days=1)
    else:
        end = context.parse(end_datetime, assume_local=True) if end_datetime else start + timedelta(hours=1)
    if end <= start:
        raise ValueError("end_datetime must be later than start_datetime.")

    draft = {
        "uid": "draft-event",
        "summary": title.strip() or "Новое событие",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "all_day": all_day,
    }
    if existing_events is None:
        start_local = start.astimezone(context.zone) - timedelta(days=1)
        end_local = end.astimezone(context.zone) + timedelta(days=1)
        loaded = list_events(start_local.isoformat(), end_local.isoformat())
        if not isinstance(loaded, list):
            raise ValueError("calendar returned an invalid response")
        existing_events = loaded
    comparable_events = [
        item for item in existing_events
        if str(item.get("uid", "")) != str(exclude_uid or "")
    ]
    result = detect_conflicts(
        temporal_context=context,
        events=[draft, *comparable_events],
        horizon_days=365,
        include_external=True,
    )
    return [
        item for item in result.get("conflicts", [])
        if item.get("event_uid") == draft["uid"]
        or item.get("related_event_uid") == draft["uid"]
    ]
