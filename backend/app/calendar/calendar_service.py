"""Provider-neutral calendar operations shared by every product surface."""

from __future__ import annotations

import os
from typing import Any

from backend.app.calendar.local_calendar import (
    create_event as create_local_event,
    delete_event as delete_local_event,
    list_events as list_local_events,
    modify_event as modify_local_event,
    search_events as search_local_events,
)
from backend.app.connectors.caldav_connector import (
    create_event as create_caldav_event,
    delete_event as delete_caldav_event,
    has_configured_credentials,
    list_calendars as list_caldav_calendars,
    list_events as list_caldav_events,
    modify_event as modify_caldav_event,
    search_events as search_caldav_events,
)
from backend.app.core.execution_mode import is_dry_run


def use_local_calendar() -> bool:
    """Return the configured calendar source used by all consumers."""
    provider = os.getenv("CALENDAR_PROVIDER", "caldav").strip().lower()
    if provider in {"local", "sqlite"}:
        return True
    if provider in {"caldav", "icloud", "external"}:
        return False
    return not has_configured_credentials()


def has_calendar_credentials() -> bool:
    return has_configured_credentials()


def _ensure_external_ready() -> None:
    if not has_configured_credentials():
        raise RuntimeError("CalDAV credentials are not configured.")


def list_calendars() -> list[dict[str, Any]] | Any:
    if use_local_calendar():
        return [{"calendar_id": "local", "calendar_name": "Mira", "calendar_color": ""}]
    _ensure_external_ready()
    return list_caldav_calendars()


def list_events(start_date: str, end_date: str) -> list[dict[str, Any]] | dict[str, Any]:
    if use_local_calendar():
        return list_local_events(start_date, end_date)
    _ensure_external_ready()
    return list_caldav_events(start_date, end_date)


def search_events(query: str) -> list[dict[str, Any]] | dict[str, Any]:
    if use_local_calendar():
        return search_local_events(query)
    _ensure_external_ready()
    return search_caldav_events(query)


def _dry_run(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "dry_run", "would_do": {"action": action, **payload}}


def create_event(
    *,
    title: str,
    start_datetime: str,
    end_datetime: str | None = None,
    description: str | None = None,
    all_day: bool = False,
    recurrence: str | None = None,
    recurrence_until: str | None = None,
    reminder_minutes: int | None = None,
    calendar_id: str | None = None,
    enforce_execution_mode: bool = False,
) -> dict[str, Any]:
    payload = {
        "title": title,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "description": description,
        "all_day": all_day,
        "recurrence": recurrence,
        "recurrence_until": recurrence_until,
        "reminder_minutes": reminder_minutes,
        "calendar_id": calendar_id,
    }
    if use_local_calendar():
        if enforce_execution_mode and is_dry_run():
            return _dry_run("create_event", payload)
        return create_local_event(
            title=title,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            description=description,
            all_day=all_day,
            recurrence=recurrence,
            recurrence_until=recurrence_until,
            reminder_minutes=reminder_minutes,
        )
    _ensure_external_ready()
    return create_caldav_event(**payload)


def modify_event(
    event_uid: str,
    updated_fields: dict[str, Any],
    *,
    enforce_execution_mode: bool = False,
) -> dict[str, Any]:
    if use_local_calendar():
        if enforce_execution_mode and is_dry_run():
            return _dry_run("modify_event", {"event_uid": event_uid, "updated_fields": updated_fields})
        return modify_local_event(event_uid, updated_fields)
    _ensure_external_ready()
    return modify_caldav_event(event_uid, updated_fields)


def delete_event(event_uid: str, *, enforce_execution_mode: bool = False) -> dict[str, Any]:
    if use_local_calendar():
        if enforce_execution_mode and is_dry_run():
            return _dry_run("delete_event", {"event_uid": event_uid})
        return delete_local_event(event_uid)
    _ensure_external_ready()
    return delete_caldav_event(event_uid)
