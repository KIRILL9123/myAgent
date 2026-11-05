import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.sandbox_service import (
    SandboxError,
    capture_baseline,
    delete_file,
    diff_workspace,
    list_files,
    read_file,
    run_check,
    runtime_status,
    request_apply,
    workspace_snapshot,
    write_file,
)

router = APIRouter()


class SandboxFileWrite(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=256 * 1024)
    overwrite: bool = False


class SandboxCheck(BaseModel):
    check: Literal["python", "pytest", "node", "compile_python"] = "python"
    path: str = Field(min_length=1, max_length=240)
    timeout_seconds: int = Field(default=30, ge=1, le=120)


async def _sandbox_call(func, *args, **kwargs):
    try:
        result = await asyncio.to_thread(func, *args, **kwargs)
    except SandboxError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Sandbox operation failed."))
    return result


@router.get("/runtime")
async def api_sandbox_runtime():
    return await _sandbox_call(runtime_status)


@router.get("/{session_id}")
async def api_sandbox_snapshot(session_id: str):
    return await _sandbox_call(workspace_snapshot, session_id)


@router.get("/{session_id}/files")
async def api_sandbox_files(session_id: str):
    return await _sandbox_call(list_files, session_id)


@router.get("/{session_id}/diff")
async def api_sandbox_diff(session_id: str):
    return await _sandbox_call(diff_workspace, session_id)


@router.post("/{session_id}/baseline")
async def api_sandbox_baseline(session_id: str):
    return await _sandbox_call(capture_baseline, session_id)


@router.post("/{session_id}/apply")
async def api_sandbox_apply(session_id: str):
    return await _sandbox_call(request_apply, session_id)


@router.get("/{session_id}/file")
async def api_sandbox_read_file(
    session_id: str,
    path: str = Query(..., min_length=1, max_length=240),
):
    return await _sandbox_call(read_file, session_id, path)


@router.post("/{session_id}/files")
async def api_sandbox_write_file(session_id: str, request: SandboxFileWrite):
    return await _sandbox_call(
        write_file,
        session_id,
        request.path,
        request.content,
        overwrite=request.overwrite,
    )


@router.delete("/{session_id}/file")
async def api_sandbox_delete_file(
    session_id: str,
    path: str = Query(..., min_length=1, max_length=240),
):
    return await _sandbox_call(delete_file, session_id, path)


@router.post("/{session_id}/checks")
async def api_sandbox_run_check(session_id: str, request: SandboxCheck):
    return await _sandbox_call(
        run_check,
        session_id,
        request.check,
        request.path,
        timeout_seconds=request.timeout_seconds,
    )
