from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.app.state.state_service import (
    build_state_report,
    build_state_snapshot,
    get_state_history,
)

router = APIRouter()


@router.get("/")
async def api_state_snapshot(include_external: bool = Query(default=True)):
    try:
        return build_state_snapshot(include_external=include_external)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state snapshot unavailable: {exc}")


@router.get("/report")
async def api_state_report(include_external: bool = Query(default=True), days: int = Query(default=30, ge=1, le=365)):
    try:
        return build_state_report(include_external=include_external, history_days=days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state report unavailable: {exc}")


@router.get("/history")
async def api_state_history(days: int = Query(default=30, ge=1, le=365)):
    try:
        return {"history": get_state_history(days)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state history unavailable: {exc}")


@router.get("/at")
async def api_state_snapshot_at(reference_time: str, include_external: bool = Query(default=False)):
    try:
        parsed = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
        return build_state_snapshot(parsed, include_external=include_external)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"state snapshot unavailable: {exc}")
