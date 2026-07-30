import asyncio

from fastapi import APIRouter, Query

from backend.app.observability.system_status import get_system_status
from backend.app.observability.telemetry import get_recent_events, get_telemetry_summary

router = APIRouter()


@router.get("/status")
async def api_system_status():
    return await asyncio.to_thread(get_system_status)


@router.get("/telemetry")
async def api_telemetry(hours: int = Query(default=24, ge=1, le=168)):
    return get_telemetry_summary(hours)


@router.get("/events")
async def api_recent_events(limit: int = Query(default=50, ge=1, le=200)):
    return {"events": get_recent_events(limit)}
