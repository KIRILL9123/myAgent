from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.commitments.commitment_service import (
    create_commitment,
    expire_overdue,
    get_commitment,
    get_commitment_events,
    link_calendar_event,
    list_commitments,
    transition_commitment,
    unlink_calendar_event,
    update_commitment,
)

router = APIRouter()


class CommitmentCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    source_type: str = "CHAT"
    source_ref: str | None = None
    owner: str = "user"
    deadline_at: str | None = None
    reminder_at: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: dict[str, Any] = Field(default_factory=dict)
    related_fact_ids: list[int] = Field(default_factory=list)
    related_calendar_event_ids: list[str] = Field(default_factory=list)
    conflicts_with_ids: list[str] = Field(default_factory=list)


class CommitmentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    owner: str | None = None
    deadline_at: str | None = None
    reminder_at: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ApprovalRequest(BaseModel):
    provenance: dict[str, Any] = Field(default_factory=dict)


class CalendarLinkRequest(BaseModel):
    event_id: str = Field(min_length=1)
    deadline_at: str | None = None


def _error(exc: Exception, not_found: int = 400) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc).strip("'"))
    return HTTPException(status_code=not_found, detail=str(exc))


@router.post("/")
async def api_create_commitment(req: CommitmentCreateRequest):
    try:
        return create_commitment(**req.model_dump())
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.get("/")
async def api_list_commitments(
    status: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    include_completed: bool = Query(default=True),
):
    try:
        return {"commitments": list_commitments(status, owner, include_completed)}
    except ValueError as exc:
        raise _error(exc)


@router.get("/{commitment_id}")
async def api_get_commitment(commitment_id: str):
    commitment = get_commitment(commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="commitment not found")
    return commitment


@router.get("/{commitment_id}/events")
async def api_get_commitment_events(commitment_id: str):
    try:
        return {"events": get_commitment_events(commitment_id)}
    except KeyError as exc:
        raise _error(exc)


@router.patch("/{commitment_id}")
async def api_update_commitment(commitment_id: str, req: CommitmentUpdateRequest):
    try:
        changes = {key: value for key, value in req.model_dump().items() if value is not None}
        return update_commitment(commitment_id, **changes)
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{commitment_id}/approve")
async def api_approve_commitment(commitment_id: str, req: ApprovalRequest):
    try:
        return transition_commitment(commitment_id, "approve", req.provenance)
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{commitment_id}/complete")
async def api_complete_commitment(commitment_id: str):
    try:
        return transition_commitment(commitment_id, "complete")
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{commitment_id}/cancel")
async def api_cancel_commitment(commitment_id: str):
    try:
        return transition_commitment(commitment_id, "cancel")
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{commitment_id}/reopen")
async def api_reopen_commitment(commitment_id: str):
    try:
        return transition_commitment(commitment_id, "reopen")
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/{commitment_id}/calendar-links")
async def api_link_calendar_event(commitment_id: str, req: CalendarLinkRequest):
    try:
        return link_calendar_event(commitment_id, req.event_id, req.deadline_at)
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.delete("/{commitment_id}/calendar-links/{event_id}")
async def api_unlink_calendar_event(commitment_id: str, event_id: str):
    try:
        return unlink_calendar_event(commitment_id, event_id)
    except (ValueError, KeyError) as exc:
        raise _error(exc)


@router.post("/maintenance/expire-overdue")
async def api_expire_overdue(now: str | None = None):
    try:
        return {"expired": expire_overdue(now)}
    except ValueError as exc:
        raise _error(exc)
