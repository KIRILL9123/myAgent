from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from backend.app.connectors.caldav_connector import (
    list_events,
    create_event,
    modify_event,
    delete_event
)
from backend.app.api.utils import run_api_tool
from backend.app.commitments.commitment_service import (
    commitments_for_calendar_events,
    link_calendar_event,
    unlink_calendar_event,
)

router = APIRouter()

class EventCreate(BaseModel):
    title: str
    start_datetime: str
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    commitment_id: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None

@router.get("/events")
async def api_list_events(start_date: str = Query(...), end_date: str = Query(...)):
    events = await run_api_tool(list_events, start_date, end_date)
    if not isinstance(events, list):
        return events
    linked = commitments_for_calendar_events([event.get("uid", "") for event in events])
    return [{**event, "commitments": linked.get(event.get("uid", ""), [])} for event in events]

@router.post("/events")
async def api_create_event(event: EventCreate):
    created = await run_api_tool(
        create_event,
        title=event.title,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        description=event.description
    )
    if event.commitment_id and created.get("status") == "created" and created.get("uid"):
        link_calendar_event(event.commitment_id, created["uid"])
    return created

@router.put("/events/{uid}")
async def api_modify_event(uid: str, event: EventUpdate):
    updated_fields = {k: v for k, v in event.dict().items() if v is not None}
    return await run_api_tool(modify_event, uid, updated_fields)

@router.delete("/events/{uid}")
async def api_delete_event(uid: str):
    deleted = await run_api_tool(delete_event, uid)
    if deleted.get("status") == "deleted":
        from backend.app.commitments.commitment_service import list_commitments
        for commitment in list_commitments(include_completed=True):
            if uid in commitment["related_calendar_event_ids"]:
                unlink_calendar_event(commitment["id"], uid)
    return deleted
