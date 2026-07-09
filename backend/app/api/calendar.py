from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any
import asyncio

from backend.app.connectors.caldav_connector import (
    list_events,
    create_event,
    modify_event,
    delete_event
)

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
    try:
        events = await asyncio.to_thread(list_events, start_date, end_date)
        if events and isinstance(events, list) and len(events) > 0 and isinstance(events[0], dict) and "error" in events[0]:
            raise HTTPException(status_code=400, detail=events[0]["error"])
        return events
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events")
async def api_create_event(event: EventCreate):
    try:
        result = await asyncio.to_thread(
            create_event,
            title=event.title,
            start_datetime=event.start_datetime,
            end_datetime=event.end_datetime,
            description=event.description
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{uid}")
async def api_modify_event(uid: str, event: EventUpdate):
    try:
        # Build updated fields dictionary, filtering out None values
        updated_fields = {k: v for k, v in event.dict().items() if v is not None}
        result = await asyncio.to_thread(modify_event, uid, updated_fields)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/{uid}")
async def api_delete_event(uid: str):
    try:
        result = await asyncio.to_thread(delete_event, uid)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
