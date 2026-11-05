"""Read-only availability search for Mira's personal calendar."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from backend.app.calendar.calendar_service import list_events
from backend.app.conflicts.preference_conflict_service import extract_calendar_preferences
from backend.app.temporal.time_context import TemporalContext, build_temporal_context


DEFAULT_EARLIEST_TIME = "09:00"
DEFAULT_LATEST_TIME = "18:00"
SLOT_STEP_MINUTES = 15
MAX_RANGE_DAYS = 31


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name}; use YYYY-MM-DD.") from exc


def _parse_time(value: str | None, default: str, field_name: str) -> time:
    raw = (value or default).strip()
    if raw.isdigit() and len(raw) <= 2:
        raw = f"{int(raw):02d}:00"
    try:
        parsed = time.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}; use HH:MM.") from exc
    if parsed.second or parsed.microsecond:
        raise ValueError(f"Invalid {field_name}; use HH:MM.")
    return parsed


def _event_interval(event: dict[str, Any], context: TemporalContext) -> tuple[datetime, datetime] | None:
    start = context.parse(event.get("start"), assume_local=True)
    end = context.parse(event.get("end"), assume_local=True)
    if not start:
        return None
    if not end or end <= start:
        end = start + timedelta(hours=1)
    return start.astimezone(context.zone), end.astimezone(context.zone)


def _preference_window(
    earliest: time,
    latest: time,
    preferences: list[dict[str, Any]],
) -> tuple[time, time, set[int]]:
    blocked_weekdays: set[int] = set()
    effective_earliest = earliest
    effective_latest = latest
    for rule in preferences:
        kind = rule.get("kind")
        if kind == "blocked_weekday":
            blocked_weekdays.add(int(rule["value"]))
        elif kind == "earliest_start":
            effective_earliest = max(effective_earliest, time.fromisoformat(str(rule["value"])))
        elif kind == "latest_end":
            effective_latest = min(effective_latest, time.fromisoformat(str(rule["value"])))
    return effective_earliest, effective_latest, blocked_weekdays


def find_calendar_slots(
    start_date: str,
    end_date: str,
    *,
    duration_minutes: int = 60,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    max_results: int = 5,
    timezone_name: str | None = None,
    temporal_context: TemporalContext | None = None,
) -> dict[str, Any]:
    """Find the first free local-time slots without changing calendar data."""
    context = temporal_context or build_temporal_context(timezone_name=timezone_name)
    start_day = _parse_date(start_date, "start_date")
    end_day = _parse_date(end_date, "end_date")
    if end_day < start_day:
        raise ValueError("end_date must be on or after start_date.")
    if (end_day - start_day).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(f"Date range must be no longer than {MAX_RANGE_DAYS} days.")
    duration_minutes = int(duration_minutes)
    if duration_minutes < 15 or duration_minutes > 1440:
        raise ValueError("duration_minutes must be between 15 and 1440.")
    max_results = int(max_results)
    if max_results < 1 or max_results > 20:
        raise ValueError("max_results must be between 1 and 20.")

    requested_earliest = _parse_time(earliest_time, DEFAULT_EARLIEST_TIME, "earliest_time")
    requested_latest = _parse_time(latest_time, DEFAULT_LATEST_TIME, "latest_time")
    preferences = extract_calendar_preferences()
    effective_earliest, effective_latest, blocked_weekdays = _preference_window(
        requested_earliest,
        requested_latest,
        preferences,
    )
    if effective_earliest >= effective_latest:
        return {
            "status": "no_slots",
            "reason": "Memory preferences leave no usable time inside the requested daily window.",
            "timezone": context.timezone_name,
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "duration_minutes": duration_minutes,
            "requested_window": {
                "earliest_time": requested_earliest.isoformat(timespec="minutes"),
                "latest_time": requested_latest.isoformat(timespec="minutes"),
            },
            "effective_window": {
                "earliest_time": effective_earliest.isoformat(timespec="minutes"),
                "latest_time": effective_latest.isoformat(timespec="minutes"),
                "blocked_weekdays": sorted(blocked_weekdays),
            },
            "events_checked": 0,
            "slots": [],
            "preferences_applied": len(preferences),
        }

    window_start = datetime.combine(start_day, time.min, tzinfo=context.zone)
    window_end = datetime.combine(end_day + timedelta(days=1), time.min, tzinfo=context.zone)
    loaded_events = list_events(window_start.isoformat(), window_end.isoformat())
    if not isinstance(loaded_events, list):
        raise ValueError("calendar returned an invalid response")
    busy_intervals = [interval for event in loaded_events if (interval := _event_interval(event, context))]

    slots: list[dict[str, Any]] = []
    current_day = start_day
    duration = timedelta(minutes=duration_minutes)
    now_local = context.now_local
    while current_day <= end_day and len(slots) < max_results:
        if current_day.weekday() not in blocked_weekdays:
            cursor = datetime.combine(current_day, effective_earliest, tzinfo=context.zone)
            day_end = datetime.combine(current_day, effective_latest, tzinfo=context.zone)
            if current_day == now_local.date():
                rounded_now = now_local.replace(second=0, microsecond=0)
                remainder = rounded_now.minute % SLOT_STEP_MINUTES
                if remainder:
                    rounded_now += timedelta(minutes=SLOT_STEP_MINUTES - remainder)
                cursor = max(cursor, rounded_now)
            while cursor + duration <= day_end and len(slots) < max_results:
                candidate_end = cursor + duration
                collision = next(
                    (interval for interval in busy_intervals if interval[0] < candidate_end and interval[1] > cursor),
                    None,
                )
                if collision:
                    cursor = max(cursor + timedelta(minutes=SLOT_STEP_MINUTES), collision[1])
                    continue
                slots.append({
                    "start": cursor.isoformat(),
                    "end": candidate_end.isoformat(),
                    "duration_minutes": duration_minutes,
                })
                cursor = candidate_end
        current_day += timedelta(days=1)

    return {
        "status": "ok" if slots else "no_slots",
        "reason": None if slots else "No free slot matched the requested window.",
        "timezone": context.timezone_name,
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
        "duration_minutes": duration_minutes,
        "requested_window": {
            "earliest_time": requested_earliest.isoformat(timespec="minutes"),
            "latest_time": requested_latest.isoformat(timespec="minutes"),
        },
        "effective_window": {
            "earliest_time": effective_earliest.isoformat(timespec="minutes"),
            "latest_time": effective_latest.isoformat(timespec="minutes"),
            "blocked_weekdays": sorted(blocked_weekdays),
        },
        "events_checked": len(busy_intervals),
        "preferences_applied": len(preferences),
        "slots": slots,
    }
