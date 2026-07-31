from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.observability.error_reports import (
    SEVERITIES, STATUSES, create_error_report, get_error_report,
    list_error_reports, update_error_report,
)

router = APIRouter()


class ErrorReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(default="", max_length=4000)
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    component: str | None = Field(default=None, max_length=120)
    correlation_id: str | None = Field(default=None, max_length=120)
    error_type: str | None = Field(default=None, max_length=120)
    context: dict[str, Any] = Field(default_factory=dict)


class ErrorReportUpdate(BaseModel):
    status: Literal["new", "fixing", "fixed", "verified", "closed"]
    fix_reference: str | None = Field(default=None, max_length=500)
    verification_result: str | None = Field(default=None, max_length=2000)
    resolution_note: str | None = Field(default=None, max_length=2000)


@router.get("")
@router.get("/")
async def api_list_errors(
    status: str = Query(default="all"),
    limit: int = Query(default=100, ge=1, le=200),
):
    try:
        return list_error_reports(status, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("")
async def api_create_error(req: ErrorReportCreate):
    try:
        return create_error_report(**req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{report_id}")
async def api_get_error(report_id: int):
    report = get_error_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="error report not found")
    return report


@router.patch("/{report_id}")
async def api_update_error(report_id: int, req: ErrorReportUpdate):
    try:
        return update_error_report(report_id, **req.model_dump())
    except ValueError as exc:
        status = 404 if str(exc) == "error report not found" else 400
        raise HTTPException(status_code=status, detail=str(exc))
