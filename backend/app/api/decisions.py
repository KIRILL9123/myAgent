from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.memory.decision_service import create_decision, list_decisions, update_decision

router = APIRouter()


class DecisionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    decision_text: str = Field(min_length=1, max_length=10000)
    rationale: str | None = Field(default=None, max_length=10000)
    alternatives: list[str] = Field(default_factory=list, max_length=20)
    status: str = "ACTIVE"
    decided_at: str | None = None
    review_at: str | None = None
    source_type: str = "MANUAL"
    provenance: dict[str, Any] = Field(default_factory=dict)


class DecisionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    decision_text: str | None = Field(default=None, min_length=1, max_length=10000)
    rationale: str | None = Field(default=None, max_length=10000)
    alternatives: list[str] | None = Field(default=None, max_length=20)
    status: str | None = None
    decided_at: str | None = None
    review_at: str | None = None


def _error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404 if isinstance(exc, KeyError) else 400, detail=str(exc).strip("'"))


@router.get("")
async def api_list_decisions(status: str | None = Query(default=None), query: str | None = Query(default=None, max_length=200)):
    try:
        return {"decisions": list_decisions(status, query)}
    except ValueError as exc:
        raise _error(exc)


@router.post("")
async def api_create_decision(req: DecisionRequest):
    try:
        return create_decision(**req.model_dump())
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.patch("/{decision_id}")
async def api_update_decision(decision_id: str, req: DecisionUpdateRequest):
    try:
        return update_decision(decision_id, **{key: value for key, value in req.model_dump().items() if value is not None})
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{decision_id}/revisit")
async def api_revisit_decision(decision_id: str):
    try:
        return update_decision(decision_id, status="REVISIT")
    except (ValueError, KeyError) as exc:
        raise _error(exc)
