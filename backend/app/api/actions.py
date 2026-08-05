from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.action_center_service import build_action_center
from backend.app.action_state_service import set_action_state
from backend.app.api.utils import run_blocking
from backend.app.notifications.delivery_service import get_notification_preferences

router = APIRouter()


class SnoozeRequest(BaseModel):
    snoozed_until: datetime


@router.get("")
@router.get("/")
async def api_action_center(
    mode: str = Query(default="attention", pattern="^(attention|all)$"),
    limit: int = Query(default=25, ge=1, le=100),
    include_external: bool = Query(default=False),
    reference_time: str | None = Query(default=None),
):
    try:
        parsed = datetime.fromisoformat(reference_time.replace("Z", "+00:00")) if reference_time else None
        preferences = get_notification_preferences()
        return await run_blocking(
            build_action_center,
            parsed,
            timezone_name=preferences["timezone"],
            mode=mode,
            limit=limit,
            include_external=include_external,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"action center unavailable: {exc}")


@router.post("/{action_id}/read")
async def api_mark_action_read(action_id: str):
    try:
        return await run_blocking(set_action_state, action_id, "read")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{action_id}/unread")
async def api_mark_action_unread(action_id: str):
    try:
        return await run_blocking(set_action_state, action_id, "unread")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{action_id}/snooze")
async def api_snooze_action(action_id: str, request: SnoozeRequest):
    try:
        return await run_blocking(set_action_state, action_id, "snoozed", snoozed_until=request.snoozed_until)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{action_id}/dismiss")
async def api_dismiss_action(action_id: str):
    try:
        return await run_blocking(set_action_state, action_id, "dismissed")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
