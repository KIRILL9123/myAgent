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

router = APIRouter()

class EventCreate(BaseModel):
    title: str
    start_datetime: str
    end_datetime: Optional[str] = None
    description: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None

@router.get("/events")
async def api_list_events(start_date: str = Query(...), end_date: str = Query(...)):
    return await run_api_tool(list_events, start_date, end_date)

@router.post("/events")
async def api_create_event(event: EventCreate):
    return await run_api_tool(
        create_event,
        title=event.title,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        description=event.description
    )

@router.put("/events/{uid}")
async def api_modify_event(uid: str, event: EventUpdate):
    updated_fields = {k: v for k, v in event.dict().items() if v is not None}
    return await run_api_tool(modify_event, uid, updated_fields)

@router.delete("/events/{uid}")
async def api_delete_event(uid: str):
    return await run_api_tool(delete_event, uid)
