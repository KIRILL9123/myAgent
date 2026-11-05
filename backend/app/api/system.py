import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.agent import llm
from backend.app.observability.system_status import get_system_status
from backend.app.observability.host_diagnostics import get_host_diagnostics
from backend.app.observability.telemetry import get_recent_events, get_telemetry_summary

router = APIRouter()


class LLMProviderUpdate(BaseModel):
    provider: Literal["local", "deepseek"]


class LLMModelsUpdate(BaseModel):
    provider: Literal["local", "deepseek"]
    main: str | None = Field(default=None, min_length=1, max_length=200)
    extractor: str | None = Field(default=None, min_length=1, max_length=200)
    classifier: str | None = Field(default=None, min_length=1, max_length=200)


@router.get("/status")
async def api_system_status():
    return await asyncio.to_thread(get_system_status)


@router.get("/llm")
async def api_llm_status():
    return llm.get_provider_status()


@router.post("/llm/provider")
async def api_set_llm_provider(payload: LLMProviderUpdate):
    try:
        return llm.set_active_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/llm/models")
async def api_set_llm_models(payload: LLMModelsUpdate):
    try:
        return llm.set_provider_models(payload.provider, payload.model_dump(exclude={"provider"}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/llm/check")
async def api_check_llm_provider(provider: Literal["local", "deepseek"] | None = None):
    return await llm.check_provider(provider)


@router.get("/host")
async def api_host_diagnostics():
    return await asyncio.to_thread(get_host_diagnostics)


@router.get("/telemetry")
async def api_telemetry(hours: int = Query(default=24, ge=1, le=168)):
    return get_telemetry_summary(hours)


@router.get("/events")
async def api_recent_events(limit: int = Query(default=50, ge=1, le=200)):
    return {"events": get_recent_events(limit)}
