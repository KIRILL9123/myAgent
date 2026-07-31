from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.app.documents.document_service import (
    archive_document,
    get_document,
    ingest_document,
    list_documents,
    search_documents,
)

router = APIRouter()


@router.get("")
async def api_list_documents(status: str = Query(default="active")):
    try:
        return {"documents": list_documents(status)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/upload")
async def api_upload_document(file: UploadFile = File(...)):
    try:
        payload = await file.read()
        return ingest_document(file.filename or "document", payload, file.content_type or "application/octet-stream")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить документ: {type(exc).__name__}")


@router.get("/search")
async def api_search_documents(query: str = Query(min_length=1, max_length=300), limit: int = Query(default=8, ge=1, le=20)):
    return {"results": search_documents(query, limit)}


@router.get("/{document_id}")
async def api_get_document(document_id: int):
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return document


@router.post("/{document_id}/archive")
async def api_archive_document(document_id: int):
    if not archive_document(document_id):
        raise HTTPException(status_code=404, detail="Документ не найден или уже архивирован")
    return {"status": "archived", "document_id": document_id}
