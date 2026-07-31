from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.agent.orchestrator import run_orchestrator
from backend.app.storage.db import get_history

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    tool_calls: list[str] = []
    requires_confirmation: bool = False
    weather: dict | None = None
    web_sources: list[dict] | None = None
    memory_used: list[dict] | None = None
    documents_used: list[dict] | None = None

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        result = await run_orchestrator(request.message, session_id=request.session_id)
        return ChatResponse(
            response=result.get("response", ""),
            tool_calls=result.get("tool_calls", []),
            requires_confirmation=result.get("requires_confirmation", False),
            weather=result.get("weather"),
            web_sources=result.get("web_sources"),
            memory_used=result.get("memory_used"),
            documents_used=result.get("documents_used"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
async def history_endpoint(session_id: str):
    try:
        # get_history returns a list of {"role": str, "content": str, "tool_calls": dict}
        history = get_history(session_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

