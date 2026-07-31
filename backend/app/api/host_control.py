from fastapi import APIRouter

from backend.app.host_control.host_control_service import get_capabilities

router = APIRouter()


@router.get("/capabilities")
async def api_host_control_capabilities():
    return get_capabilities()
