from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.notifications.delivery_service import (
    get_notification_preferences,
    update_notification_preferences,
)

router = APIRouter()


class NotificationPreferencesUpdate(BaseModel):
    enabled: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    max_messages_per_window: int | None = Field(default=None, ge=1, le=50)
    window_minutes: int | None = Field(default=None, ge=5, le=1440)
    min_priority: str | None = None
    coalesce_window_minutes: int | None = Field(default=None, ge=1, le=1440)


@router.get("/preferences")
async def api_get_notification_preferences():
    return get_notification_preferences()


@router.put("/preferences")
async def api_update_notification_preferences(req: NotificationPreferencesUpdate):
    try:
        return update_notification_preferences(**req.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
