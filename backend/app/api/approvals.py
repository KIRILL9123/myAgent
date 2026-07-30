from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.approvals.approval_service import list_approvals, resolve_approval

router = APIRouter()


class ApprovalResolutionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


@router.get("/")
async def api_list_approvals(status: str = Query(default="PENDING")):
    if status.upper() not in {"PENDING", "APPROVED", "REJECTED", "FAILED"}:
        raise HTTPException(status_code=400, detail="invalid approval status")
    return {"approvals": list_approvals(status)}


@router.post("/{approval_id}/approve")
async def api_approve(approval_id: str, req: ApprovalResolutionRequest):
    try:
        return await resolve_approval(approval_id, "approve", req.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{approval_id}/reject")
async def api_reject(approval_id: str, req: ApprovalResolutionRequest):
    try:
        return await resolve_approval(approval_id, "reject", req.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
