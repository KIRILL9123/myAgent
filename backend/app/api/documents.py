from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from backend.app.api.utils import run_api_tool
from backend.app.documents import document_service

from backend.app.documents.document_service import (
    archive_document,
    get_document,
    ingest_document,
    list_documents,
    search_documents,
)
from backend.app.documents.document_link_service import (
    create_document_link,
    delete_document_link,
    list_document_link_targets,
    list_document_links,
)
from backend.app.documents.document_proposal_service import (
    create_document_proposal,
    scan_document_proposals,
)

router = APIRouter()


class DocumentLinkCreateRequest(BaseModel):
    target_type: Literal["commitment", "calendar_event", "subscription"]
    target_id: str = Field(min_length=1, max_length=200)
    target_label: str = Field(min_length=1, max_length=300)
    relationship: str = Field(default="related", min_length=1, max_length=80)


class DocumentProposalCreateRequest(BaseModel):
    candidate_id: str = Field(min_length=1, max_length=64)
    action_type: Literal["commitment", "calendar_event"]


@router.get("")
async def api_list_documents(status: str = Query(default="active")):
    try:
        return {"documents": await run_api_tool(list_documents, status)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload")
async def api_upload_document(file: UploadFile = File(...)):
    try:
        payload = await file.read(document_service.MAX_DOCUMENT_BYTES + 1)
        if len(payload) > document_service.MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=400, detail="Размер документа превышает допустимый лимит")
        return await run_api_tool(
            ingest_document,
            file.filename or "document",
            payload,
            file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить документ: {type(exc).__name__}")


@router.get("/search")
async def api_search_documents(query: str = Query(min_length=1, max_length=300), limit: int = Query(default=8, ge=1, le=20)):
    return {"results": await run_api_tool(search_documents, query, limit)}


@router.get("/link-targets")
async def api_document_link_targets():
    return {"targets": await run_api_tool(list_document_link_targets)}


@router.get("/{document_id}/links")
async def api_list_document_links(document_id: int):
    try:
        return {"links": await run_api_tool(list_document_links, document_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'"))


@router.post("/{document_id}/links")
async def api_create_document_link(document_id: int, request: DocumentLinkCreateRequest):
    try:
        return await run_api_tool(create_document_link, document_id, **request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{document_id}/links/{link_id}", status_code=204)
async def api_delete_document_link(document_id: int, link_id: int):
    if not await run_api_tool(delete_document_link, document_id, link_id):
        raise HTTPException(status_code=404, detail="Связь документа не найдена")
    return None


@router.get("/{document_id}/proposals")
async def api_scan_document_proposals(document_id: int):
    try:
        return await run_api_tool(scan_document_proposals, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{document_id}/proposals")
async def api_create_document_proposal(document_id: int, request: DocumentProposalCreateRequest):
    try:
        return await run_api_tool(
            create_document_proposal,
            document_id,
            request.candidate_id,
            request.action_type,
            "web",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{document_id}")
async def api_get_document(document_id: int):
    document = await run_api_tool(get_document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return document


@router.post("/{document_id}/archive")
async def api_archive_document(document_id: int):
    if not await run_api_tool(archive_document, document_id):
        raise HTTPException(status_code=404, detail="Документ не найден или уже архивирован")
    return {"status": "archived", "document_id": document_id}
