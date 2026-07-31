from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from backend.app.action_center_service import build_action_center

router = APIRouter()


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
        return build_action_center(parsed, mode=mode, limit=limit, include_external=include_external)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"action center unavailable: {exc}")
