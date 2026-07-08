from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.app.countdown.countdown_service import (
    add_countdown,
    get_all_countdowns,
    delete_countdown
)

router = APIRouter()

class CountdownCreateRequest(BaseModel):
    title: str
    target_date: str
    category: str = "другое"

@router.post("/")
async def api_add_countdown(req: CountdownCreateRequest):
    result = add_countdown(
        title=req.title,
        target_date=req.target_date,
        category=req.category
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.get("/")
async def api_get_countdowns():
    result = get_all_countdowns()
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result

@router.delete("/{countdown_id}")
async def api_delete_countdown(countdown_id: int):
    result = delete_countdown(countdown_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result
