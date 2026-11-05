from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from backend.app.api.utils import run_blocking

from backend.app.state.state_service import (
    build_state_report,
    build_state_snapshot,
    get_state_history,
)
from backend.app.notifications.delivery_service import get_notification_preferences

router = APIRouter()


@router.get("/")
async def api_state_snapshot(include_external: bool = Query(default=True)):
    try:
        return await run_blocking(
            build_state_snapshot,
            timezone_name=get_notification_preferences()["timezone"],
            include_external=include_external,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state snapshot unavailable: {exc}")


@router.get("/report")
async def api_state_report(include_external: bool = Query(default=True), days: int = Query(default=30, ge=1, le=365)):
    try:
        return await run_blocking(
            build_state_report,
            timezone_name=get_notification_preferences()["timezone"],
            include_external=include_external,
            history_days=days,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state report unavailable: {exc}")


@router.get("/history")
async def api_state_history(days: int = Query(default=30, ge=1, le=365)):
    try:
        history = await run_blocking(
            get_state_history,
            days,
            timezone_name=get_notification_preferences()["timezone"],
        )
        return {"history": history}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state history unavailable: {exc}")


@router.get("/at")
async def api_state_snapshot_at(reference_time: str, include_external: bool = Query(default=False)):
    try:
        parsed = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
        return await run_blocking(
            build_state_snapshot,
            parsed,
            timezone_name=get_notification_preferences()["timezone"],
            include_external=include_external,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state snapshot unavailable: {exc}")
