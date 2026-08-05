from datetime import datetime, time, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from backend.app.calendar.calendar_service import (
    create_event as create_calendar_event,
    delete_event as delete_calendar_event,
    has_calendar_credentials,
    list_calendars as list_calendar_calendars,
    list_events as list_calendar_events,
    modify_event as modify_calendar_event,
    search_events as search_calendar_events,
    use_local_calendar,
)
from backend.app.api.utils import run_api_tool
from backend.app.commitments.commitment_service import (
    commitments_for_calendar_events,
    link_calendar_event,
    unlink_calendar_event,
)
from backend.app.conflicts.conflict_service import detect_conflicts, preview_event_conflicts
from backend.app.notifications.delivery_service import get_notification_preferences
from backend.app.temporal.time_context import build_temporal_context

router = APIRouter()


def _raise_if_dry_run(result: dict) -> dict:
    if result.get("status") == "dry_run":
        raise HTTPException(
            status_code=409,
            detail="Календарь работает в безопасном режиме: внешнее событие не было сохранено.",
        )
    return result


def _ensure_caldav_ready() -> None:
    if not use_local_calendar() and not has_calendar_credentials():
        raise HTTPException(
            status_code=503,
            detail="Подключение к Apple Calendar не настроено. Заполните CALDAV_USERNAME и CALDAV_PASSWORD в .env.",
        )

class EventCreate(BaseModel):
    title: str
    start_datetime: str
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    commitment_id: Optional[str] = None
    all_day: bool = False
    recurrence: Optional[str] = None
    recurrence_until: Optional[str] = None
    reminder_minutes: Optional[int] = None
    calendar_id: Optional[str] = None
    allow_conflicts: bool = False

class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    all_day: Optional[bool] = None
    recurrence: Optional[str] = None
    recurrence_until: Optional[str] = None
    reminder_minutes: Optional[int] = None
    allow_conflicts: bool = False


async def _preview_update_conflicts(uid: str, event: EventUpdate) -> list[dict]:
    """Resolve the current event and run the same pre-save check for edits."""
    timezone_name = get_notification_preferences()["timezone"]
    context = build_temporal_context(timezone_name=timezone_name)
    scan_start = datetime.combine(context.today - timedelta(days=365), time.min, tzinfo=context.zone)
    scan_end = datetime.combine(context.today + timedelta(days=730), time.min, tzinfo=context.zone)
    events = await run_api_tool(list_calendar_events, scan_start.isoformat(), scan_end.isoformat())
    if not isinstance(events, list):
        return []
    current = next((item for item in events if str(item.get("uid")) == str(uid)), None)
    if not current:
        return []
    all_day = event.all_day if event.all_day is not None else bool(current.get("all_day"))
    end_was_provided = event.end_datetime is not None
    return await run_api_tool(
        preview_event_conflicts,
        title=event.title if event.title is not None else current.get("summary", "Событие"),
        start_datetime=event.start_datetime or current.get("start", ""),
        end_datetime=event.end_datetime or current.get("end"),
        all_day=all_day,
        exclude_uid=uid,
        timezone_name=timezone_name,
        existing_events=events,
        all_day_end_is_exclusive=all_day and not end_was_provided,
    )


@router.get("/calendars")
async def api_list_calendars():
    _ensure_caldav_ready()
    return await run_api_tool(list_calendar_calendars)

@router.get("/events")
async def api_list_events(start_date: str = Query(...), end_date: str = Query(...)):
    _ensure_caldav_ready()
    events = await run_api_tool(list_calendar_events, start_date, end_date)
    if not isinstance(events, list):
        return events
    linked = commitments_for_calendar_events([event.get("uid", "") for event in events])
    conflict_result = detect_conflicts(events=events, horizon_days=365, include_external=True)
    by_event_uid: dict[str, list[dict]] = {}
    for conflict in conflict_result.get("conflicts", []):
        for uid in (conflict.get("event_uid"), conflict.get("related_event_uid")):
            if uid:
                by_event_uid.setdefault(str(uid), []).append(conflict)
    return [
        {
            **event,
            "commitments": linked.get(event.get("uid", ""), []),
            "conflicts": by_event_uid.get(str(event.get("uid", "")), []),
        }
        for event in events
    ]


@router.get("/search")
async def api_search_events(query: str = Query(..., min_length=2, max_length=120)):
    _ensure_caldav_ready()
    return await run_api_tool(search_calendar_events, query)

@router.post("/events")
async def api_create_event(event: EventCreate):
    _ensure_caldav_ready()
    if not event.allow_conflicts:
        conflicts = await run_api_tool(
            preview_event_conflicts,
            title=event.title,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
            all_day=event.all_day,
            timezone_name=get_notification_preferences()["timezone"],
        )
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "calendar_conflicts",
                    "message": "Событие конфликтует с календарём или одобренным предпочтением из Memory.",
                    "conflicts": conflicts,
                },
            )
    created = await run_api_tool(
        create_calendar_event,
        title=event.title,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        description=event.description,
        all_day=event.all_day,
        recurrence=event.recurrence,
        recurrence_until=event.recurrence_until,
        reminder_minutes=event.reminder_minutes,
        calendar_id=event.calendar_id,
    )
    if not use_local_calendar():
        _raise_if_dry_run(created)
    if event.commitment_id and created.get("status") == "created" and created.get("uid"):
        link_calendar_event(event.commitment_id, created["uid"])
    return created

@router.put("/events/{uid}")
async def api_modify_event(uid: str, event: EventUpdate):
    _ensure_caldav_ready()
    if not event.allow_conflicts:
        conflicts = await _preview_update_conflicts(uid, event)
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "calendar_conflicts",
                    "message": "Изменение конфликтует с календарём или одобренным предпочтением из Memory.",
                    "conflicts": conflicts,
                },
            )
    updated_fields = {k: v for k, v in event.model_dump().items() if v is not None and k != "allow_conflicts"}
    updated = await run_api_tool(modify_calendar_event, uid, updated_fields)
    return updated if use_local_calendar() else _raise_if_dry_run(updated)

@router.delete("/events/{uid}")
async def api_delete_event(uid: str):
    _ensure_caldav_ready()
    deleted = await run_api_tool(delete_calendar_event, uid)
    if not use_local_calendar():
        deleted = _raise_if_dry_run(deleted)
    if deleted.get("status") == "deleted":
        from backend.app.commitments.commitment_service import list_commitments
        for commitment in list_commitments(include_completed=True):
            if uid in commitment["related_calendar_event_ids"]:
                unlink_calendar_event(commitment["id"], uid)
    return deleted
