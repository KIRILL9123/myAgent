import os
import time
from dotenv import load_dotenv
load_dotenv()
import caldav
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4
from icalendar import Calendar as iCalendar, Event as iEvent


# In-memory cache for client calendars and query results to bypass slow iCloud roundtrips
_cached_calendars: list[caldav.Calendar] | None = None
_cached_primary_calendar: caldav.Calendar | None = None

_events_cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}
CACHE_TTL_SECONDS = 180  # Cache query results for 3 minutes


def has_configured_credentials() -> bool:
    """Return whether CalDAV credentials look configured rather than templated."""
    username = os.getenv("CALDAV_USERNAME", "").strip()
    password = os.getenv("CALDAV_PASSWORD", "").strip()
    placeholders = {
        "your_apple_id@icloud.com",
        "your_email@icloud.com",
        "your_app_specific_password",
        "your_password",
    }
    return bool(username and password and username not in placeholders and password not in placeholders)


def is_calendar_write_allowed() -> bool:
    return os.getenv("CALENDAR_ALLOW_WRITES", "false").strip().lower() in {"1", "true", "yes", "on"}


def clear_events_cache() -> None:
    global _events_cache
    _events_cache.clear()


def get_client() -> caldav.DAVClient | None:
    url = os.getenv("CALDAV_URL", "https://caldav.icloud.com")
    username = os.getenv("CALDAV_USERNAME")
    password = os.getenv("CALDAV_PASSWORD")

    if not has_configured_credentials():
        return None

    # Adding a 15-second timeout to prevent indefinite socket hangs on slow CalDAV queries
    return caldav.DAVClient(url=url, username=username, password=password, timeout=15)


def _get_all_calendars() -> list[caldav.Calendar]:
    """Retrieve all calendars for the user, with in-memory caching."""
    global _cached_calendars
    if _cached_calendars is not None:
        return _cached_calendars

    client = get_client()
    if not client:
        return []
    try:
        principal = client.principal()
        calendars = principal.calendars()
        _cached_calendars = calendars
        return calendars
    except Exception:
        return []


def _get_primary_calendar() -> caldav.Calendar | None:
    """Returns the first available calendar (primary)."""
    global _cached_primary_calendar
    if _cached_primary_calendar is not None:
        return _cached_primary_calendar

    calendars = _get_all_calendars()
    if calendars:
        _cached_primary_calendar = calendars[0]
        return _cached_primary_calendar
    return None


def _calendar_metadata(calendar: Any) -> dict[str, str]:
    properties = getattr(calendar, "properties", {}) or {}
    color = ""
    for key in ("{http://apple.com/ns/ical/}calendar-color", "calendar-color"):
        if isinstance(properties, dict) and properties.get(key):
            color = str(properties[key])
            break
    name = getattr(calendar, "name", None) or getattr(calendar, "displayname", None) or "Календарь"
    url = getattr(calendar, "url", "")
    return {"calendar_id": str(url), "calendar_name": str(name), "calendar_color": color}


def _extract_recurrence(vevent: Any) -> tuple[str | None, str | None]:
    if not hasattr(vevent, "rrule"):
        return None, None
    try:
        values = vevent.rrule.value
        if isinstance(values, str):
            parsed = {}
            for item in values.split(";"):
                key, _, value = item.partition("=")
                if key and value:
                    parsed[key.upper()] = value
            values = parsed
        frequency = values.get("FREQ")
        if isinstance(frequency, list):
            frequency = frequency[0]
        until = values.get("UNTIL")
        if isinstance(until, list):
            until = until[0]
        if hasattr(until, "isoformat"):
            until_value = until.isoformat()
        elif until and len(str(until)) == 8 and str(until).isdigit():
            raw = str(until)
            until_value = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        else:
            until_value = str(until) if until else None
        return (str(frequency).lower() if frequency else None), until_value
    except Exception:
        return None, None


def _extract_reminder_minutes(vevent: Any) -> int | None:
    try:
        alarm = getattr(vevent, "valarm", None)
        trigger = getattr(alarm, "trigger", None)
        value = getattr(trigger, "value", None)
        if isinstance(value, timedelta):
            return max(0, int(abs(value.total_seconds()) // 60))
    except Exception:
        pass
    return None


def _extract_event_data(event: Any, calendar: Any | None = None) -> dict[str, Any]:
    """Extract calendar event fields while keeping the frontend contract stable."""
    vevent = getattr(event.vobject_instance, 'vevent', None)
    if not vevent:
        return {"summary": "No Title", "start": "Unknown", "end": "Unknown", "uid": ""}
    start_value = vevent.dtstart.value if hasattr(vevent, 'dtstart') else "Unknown"
    end_value = vevent.dtend.value if hasattr(vevent, 'dtend') else "Unknown"
    event_data = {
        "summary": vevent.summary.value if hasattr(vevent, 'summary') else "No Title",
        "start": start_value.isoformat() if hasattr(start_value, "isoformat") else str(start_value),
        "end": end_value.isoformat() if hasattr(end_value, "isoformat") else str(end_value),
        "uid": str(vevent.uid.value) if hasattr(vevent, 'uid') else "",
        "description": vevent.description.value if hasattr(vevent, 'description') else "",
        "all_day": isinstance(start_value, date) and not isinstance(start_value, datetime),
    }
    recurrence, recurrence_until = _extract_recurrence(vevent)
    if recurrence:
        event_data["recurrence"] = recurrence
    if recurrence_until:
        event_data["recurrence_until"] = recurrence_until
    reminder_minutes = _extract_reminder_minutes(vevent)
    if reminder_minutes is not None:
        event_data["reminder_minutes"] = reminder_minutes
    if calendar is not None:
        event_data.update(_calendar_metadata(calendar))
    return event_data


def list_calendars() -> list[dict[str, str]] | dict[str, str]:
    if not get_client():
        return {"status": "error", "message": "CalDAV credentials not configured."}
    return [_calendar_metadata(calendar) for calendar in _get_all_calendars()]


# ─── Read-only operations (green) ────────────────────────────────────────────

def list_events(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """
    List calendar events between start_date and end_date (ISO 8601 strings).
    Read-only operation.
    """
    client = get_client()
    if not client:
        return {"status": "error", "message": "CalDAV credentials not configured."}

    cache_key = (start_date, end_date)
    now = time.time()
    if cache_key in _events_cache:
        expiry, cached_data = _events_cache[cache_key]
        if now < expiry:
            return cached_data

    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use ISO 8601 (e.g. 2026-07-02T00:00:00)."}

    try:
        calendars = _get_all_calendars()
        events_out: list[dict[str, Any]] = []

        for calendar in calendars:
            events = calendar.date_search(start=start, end=end, expand=True)
            for event in events:
                events_out.append(_extract_event_data(event, calendar))

        _events_cache[cache_key] = (now + CACHE_TTL_SECONDS, events_out)
        return events_out
    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_events(query: str) -> Any:
    """
    Search calendar events matching the query string in their title.
    Read-only operation.
    """
    client = get_client()
    if not client:
        return {"status": "error", "message": "CalDAV credentials not configured."}

    try:
        calendars = _get_all_calendars()
        events_out: list[dict[str, Any]] = []

        for calendar in calendars:
            # iCloud doesn't reliably support full-text search via CalDAV,
            # so we fetch upcoming events and filter locally.
            start = datetime.now() - timedelta(days=3650)
            end = datetime.now() + timedelta(days=3650)
            events = calendar.date_search(start=start, end=end, expand=True)
            for event in events:
                data = _extract_event_data(event, calendar)
                if query.lower() in data["summary"].lower():
                    events_out.append(data)

        return events_out
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Write operations (yellow / red) ─────────────────────────────────────────

def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str | None = None,
    description: str | None = None,
    all_day: bool = False,
    recurrence: str | None = None,
    recurrence_until: str | None = None,
    reminder_minutes: int | None = None,
    calendar_id: str | None = None,
) -> dict[str, Any]:
    """
    Creates a new calendar event.
    Yellow permission level.
    """
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run() and not is_calendar_write_allowed():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "create_event",
                "title": title,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "description": description,
                "all_day": all_day,
                "recurrence": recurrence,
                "recurrence_until": recurrence_until,
                "reminder_minutes": reminder_minutes,
                "calendar_id": calendar_id,
            },
        }

    clear_events_cache()
    cal = _get_primary_calendar()
    if calendar_id:
        cal = next((item for item in _get_all_calendars() if str(getattr(item, "url", "")) == calendar_id), None)
    if not cal:
        return {"status": "error", "message": "CalDAV credentials not configured or no calendars found."}

    try:
        if all_day:
            start = date.fromisoformat(start_datetime[:10])
            end = date.fromisoformat(end_datetime[:10]) + timedelta(days=1) if end_datetime else start + timedelta(days=1)
        else:
            start = datetime.fromisoformat(start_datetime)
            if end_datetime:
                end = datetime.fromisoformat(end_datetime)
            else:
                end = start + timedelta(hours=1)
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use ISO 8601 (e.g. 2026-07-03T10:00:00)."}

    try:
        # Build the iCalendar VCALENDAR/VEVENT payload
        ical = iCalendar()
        ical.add("prodid", "-//HomeAgent//EN")
        ical.add("version", "2.0")

        vevent = iEvent()
        vevent.add("uid", str(uuid4()))
        vevent.add("summary", title)
        vevent.add("dtstart", start)
        vevent.add("dtend", end)
        if description:
            vevent.add("description", description)
        if recurrence and recurrence.lower() != "none":
            rule: dict[str, Any] = {"freq": recurrence.upper()}
            if recurrence_until:
                rule["until"] = date.fromisoformat(recurrence_until[:10])
            vevent.add("rrule", rule)
        if reminder_minutes is not None and reminder_minutes >= 0:
            alarm = vevent.add("valarm")
            alarm.add("action").value = "DISPLAY"
            alarm.add("description").value = title
            alarm.add("trigger").value = timedelta(minutes=-int(reminder_minutes))

        ical.add_component(vevent)

        created = cal.save_event(ical.to_ical().decode("utf-8"))
        data = _extract_event_data(created, cal)
        return {"status": "created", **data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _find_event_by_uid_or_title(identifier: str) -> tuple[Any, str] | tuple[None, str]:
    """
    Try to find an event by UID first. If that fails, search by title.
    Returns (event_object, found_method) or (None, error_message).
    """
    client = get_client()
    if not client:
        return None, "CalDAV credentials not configured."

    calendars = _get_all_calendars()

    # 1. Try by UID directly
    for calendar in calendars:
        try:
            event = calendar.event_by_uid(identifier)
            return event, "uid"
        except Exception:
            continue

    # 2. Fallback: search by UID locally
    for calendar in calendars:
        try:
            all_events = calendar.events()
            for event in all_events:
                data = _extract_event_data(event)
                if data.get("uid") and identifier.lower() == data["uid"].lower():
                    return event, "uid_fallback"
        except Exception:
            continue

    # 3. Fallback: search by title locally
    for calendar in calendars:
        try:
            all_events = calendar.events()
            for event in all_events:
                data = _extract_event_data(event)
                if identifier.lower() in data["summary"].lower():
                    return event, "title"
        except Exception:
            continue

    return None, f"Event '{identifier}' not found by UID or title."


def delete_event(event_uid: str) -> dict[str, Any]:
    """
    Deletes an event by its UID or title (fallback).
    Red permission level — requires prior human confirmation.
    """
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run() and not is_calendar_write_allowed():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "delete_event",
                "event_uid": event_uid,
            },
        }

    clear_events_cache()
    try:
        event, method = _find_event_by_uid_or_title(event_uid)
        if event is None:
            return {"status": "error", "message": method}  # method contains the error message

        data = _extract_event_data(event)
        event.delete()
        return {"status": "deleted", "found_by": method, **data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def modify_event(event_uid: str, updated_fields: dict[str, Any]) -> dict[str, Any]:
    """
    Modifies an existing event by UID or title (fallback).
    Red permission level — requires prior human confirmation.
    Supported updated_fields keys: title, start_datetime, end_datetime, description,
    all_day, recurrence, recurrence_until and reminder_minutes.
    """
    from backend.app.core.execution_mode import is_dry_run
    if is_dry_run() and not is_calendar_write_allowed():
        return {
            "status": "dry_run",
            "would_do": {
                "action": "modify_event",
                "event_uid": event_uid,
                "updated_fields": updated_fields,
            },
        }

    clear_events_cache()
    try:
        event, method = _find_event_by_uid_or_title(event_uid)
        if event is None:
            return {"status": "error", "message": method}

        vevent = event.vobject_instance.vevent
        current = _extract_event_data(event)
        all_day = bool(updated_fields.get("all_day", current.get("all_day", False)))

        if "title" in updated_fields:
            vevent.summary.value = updated_fields["title"]
        if "start_datetime" in updated_fields or "end_datetime" in updated_fields or "all_day" in updated_fields:
            start_value = updated_fields.get("start_datetime", current["start"])
            end_value = updated_fields.get("end_datetime", current["end"])
            if all_day:
                vevent.dtstart.value = date.fromisoformat(str(start_value)[:10])
                end_date = date.fromisoformat(str(end_value)[:10])
                if not (current.get("all_day") and "end_datetime" not in updated_fields):
                    end_date += timedelta(days=1)
                vevent.dtend.value = end_date
            else:
                vevent.dtstart.value = datetime.fromisoformat(str(start_value))
                vevent.dtend.value = datetime.fromisoformat(str(end_value))
        if "description" in updated_fields:
            if hasattr(vevent, "description"):
                vevent.description.value = updated_fields["description"]
            else:
                vevent.add("description").value = updated_fields["description"]
        if "recurrence" in updated_fields or "recurrence_until" in updated_fields:
            try:
                del vevent.rrule
            except (AttributeError, KeyError):
                pass
            recurrence = updated_fields.get("recurrence")
            if recurrence and recurrence != "none":
                rule: dict[str, Any] = {"freq": str(recurrence).upper()}
                recurrence_until = updated_fields.get("recurrence_until")
                if recurrence_until:
                    rule["until"] = date.fromisoformat(str(recurrence_until)[:10])
                recurrence_value = f"FREQ={str(recurrence).upper()}"
                if recurrence_until:
                    recurrence_value += f";UNTIL={str(recurrence_until)[:10].replace('-', '')}"
                vevent.add("rrule").value = recurrence_value
        if "reminder_minutes" in updated_fields:
            try:
                del vevent.valarm
            except (AttributeError, KeyError):
                pass
            reminder_minutes = updated_fields.get("reminder_minutes")
            if reminder_minutes is not None:
                alarm = vevent.add("valarm")
                alarm.add("action").value = "DISPLAY"
                alarm.add("description").value = vevent.summary.value
                alarm.add("trigger").value = timedelta(minutes=-int(reminder_minutes))

        event.save()
        return {"status": "modified", "found_by": method, **_extract_event_data(event)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

