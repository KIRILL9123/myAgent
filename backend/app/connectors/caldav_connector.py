import os
import time
from dotenv import load_dotenv
load_dotenv()
import caldav
from datetime import datetime, timedelta
from typing import Any
from icalendar import Calendar as iCalendar, Event as iEvent


# In-memory cache for client calendars and query results to bypass slow iCloud roundtrips
_cached_calendars: list[caldav.Calendar] | None = None
_cached_primary_calendar: caldav.Calendar | None = None

_events_cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}
CACHE_TTL_SECONDS = 180  # Cache query results for 3 minutes


def clear_events_cache() -> None:
    global _events_cache
    _events_cache.clear()


def get_client() -> caldav.DAVClient | None:
    url = os.getenv("CALDAV_URL", "https://caldav.icloud.com")
    username = os.getenv("CALDAV_USERNAME")
    password = os.getenv("CALDAV_PASSWORD")

    if not username or not password:
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


def _extract_event_data(event: Any) -> dict[str, Any]:
    """Extracts summary/start/end/uid from a caldav event object."""
    vevent = getattr(event.vobject_instance, 'vevent', None)
    if not vevent:
        return {"summary": "No Title", "start": "Unknown", "end": "Unknown", "uid": ""}
    return {
        "summary": vevent.summary.value if hasattr(vevent, 'summary') else "No Title",
        "start": str(vevent.dtstart.value) if hasattr(vevent, 'dtstart') else "Unknown",
        "end": str(vevent.dtend.value) if hasattr(vevent, 'dtend') else "Unknown",
        "uid": str(vevent.uid.value) if hasattr(vevent, 'uid') else "",
    }


# ─── Read-only operations (green) ────────────────────────────────────────────

def list_events(start_date: str, end_date: str) -> list[dict[str, Any]]:
    """
    List calendar events between start_date and end_date (ISO 8601 strings).
    Read-only operation.
    """
    client = get_client()
    if not client:
        return [{"error": "CalDAV credentials not configured."}]

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
        return [{"error": "Invalid date format. Use ISO 8601 (e.g. 2026-07-02T00:00:00)."}]

    try:
        calendars = _get_all_calendars()
        events_out: list[dict[str, Any]] = []

        for calendar in calendars:
            events = calendar.date_search(start=start, end=end, expand=True)
            for event in events:
                events_out.append(_extract_event_data(event))

        _events_cache[cache_key] = (now + CACHE_TTL_SECONDS, events_out)
        return events_out
    except Exception as e:
        return [{"error": str(e)}]


def search_events(query: str) -> list[dict[str, Any]]:
    """
    Search calendar events matching the query string in their title.
    Read-only operation.
    """
    client = get_client()
    if not client:
        return [{"error": "CalDAV credentials not configured."}]

    try:
        calendars = _get_all_calendars()
        events_out: list[dict[str, Any]] = []

        for calendar in calendars:
            # iCloud doesn't reliably support full-text search via CalDAV,
            # so we fetch upcoming events and filter locally.
            start = datetime.now()
            events = calendar.date_search(start=start, expand=True)
            for event in events:
                data = _extract_event_data(event)
                if query.lower() in data["summary"].lower():
                    events_out.append(data)

        return events_out
    except Exception as e:
        return [{"error": str(e)}]


# ─── Write operations (yellow / red) ─────────────────────────────────────────

def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Creates a new calendar event.
    Yellow permission level.
    """
    clear_events_cache()
    cal = _get_primary_calendar()
    if not cal:
        return {"error": "CalDAV credentials not configured or no calendars found."}

    try:
        start = datetime.fromisoformat(start_datetime)
        if end_datetime:
            end = datetime.fromisoformat(end_datetime)
        else:
            end = start + timedelta(hours=1)
    except ValueError:
        return {"error": "Invalid date format. Use ISO 8601 (e.g. 2026-07-03T10:00:00)."}

    try:
        # Build the iCalendar VCALENDAR/VEVENT payload
        ical = iCalendar()
        ical.add("prodid", "-//HomeAgent//EN")
        ical.add("version", "2.0")

        vevent = iEvent()
        vevent.add("summary", title)
        vevent.add("dtstart", start)
        vevent.add("dtend", end)
        if description:
            vevent.add("description", description)

        ical.add_component(vevent)

        created = cal.save_event(ical.to_ical().decode("utf-8"))
        data = _extract_event_data(created)
        return {"status": "created", **data}
    except Exception as e:
        return {"error": str(e)}


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
    clear_events_cache()
    try:
        event, method = _find_event_by_uid_or_title(event_uid)
        if event is None:
            return {"error": method}  # method contains the error message

        data = _extract_event_data(event)
        event.delete()
        return {"status": "deleted", "found_by": method, **data}
    except Exception as e:
        return {"error": str(e)}


def modify_event(event_uid: str, updated_fields: dict[str, str]) -> dict[str, Any]:
    """
    Modifies an existing event by UID or title (fallback).
    Red permission level — requires prior human confirmation.
    Supported updated_fields keys: title, start_datetime, end_datetime, description.
    """
    clear_events_cache()
    try:
        event, method = _find_event_by_uid_or_title(event_uid)
        if event is None:
            return {"error": method}

        vevent = event.vobject_instance.vevent

        if "title" in updated_fields:
            vevent.summary.value = updated_fields["title"]
        if "start_datetime" in updated_fields:
            vevent.dtstart.value = datetime.fromisoformat(updated_fields["start_datetime"])
        if "end_datetime" in updated_fields:
            vevent.dtend.value = datetime.fromisoformat(updated_fields["end_datetime"])
        if "description" in updated_fields:
            if hasattr(vevent, "description"):
                vevent.description.value = updated_fields["description"]
            else:
                vevent.add("description").value = updated_fields["description"]

        event.save()
        return {"status": "modified", "found_by": method, **_extract_event_data(event)}
    except Exception as e:
        return {"error": str(e)}

