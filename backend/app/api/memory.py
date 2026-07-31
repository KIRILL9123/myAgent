from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from backend.app.memory.memory_service import (
    get_pending_facts,
    approve_fact,
    reject_fact,
    get_graph_data,
    backfill_isolated_relations,
    create_note, get_note, get_memory_overview, list_facts, list_notes, search_memory,
    update_fact, update_note, confirm_fact, extract_note_facts,
)

router = APIRouter()

@router.get("/pending")
async def api_get_pending_facts():
    try:
        facts = get_pending_facts()
        return {"facts": facts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{fact_id}/approve")
async def api_approve_fact(fact_id: int):
    try:
        success = await approve_fact(fact_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Fact with ID {fact_id} could not be approved (possibly not found or already processed)."
            )
        return {"status": "success", "message": f"Fact {fact_id} approved."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{fact_id}/reject")
async def api_reject_fact(fact_id: int):
    try:
        success = reject_fact(fact_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Fact with ID {fact_id} could not be rejected (possibly not found or already processed)."
            )
        return {"status": "success", "message": f"Fact {fact_id} rejected."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph")
async def api_get_graph():
    try:
        data = get_graph_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backfill-relations")
async def api_backfill_relations():
    try:
        added_count = await backfill_isolated_relations()
        return {
            "status": "success",
            "message": f"Backfilled relationships. Added {added_count} new relations.",
            "relations_added": added_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from backend.app.memory.memory_service import find_consolidation_candidates, consolidate_facts
from backend.app.memory.skill_service import list_skills, create_skill, disable_skill

class NoteCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    tags: list[str] = Field(default_factory=list)

class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    tags: list[str] | None = None
    status: str | None = None

class FactUpdateRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    category: str | None = None
    is_pinned: bool | None = None


class SkillCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    triggers: list[str] = Field(min_length=1, max_length=20)
    steps: list[str] = Field(min_length=1, max_length=20)
    category: str = Field(default="general", min_length=1, max_length=60)

@router.get("/overview")
async def api_memory_overview():
    return get_memory_overview()


@router.get("/skills")
async def api_list_skills(status: str = "all"):
    if status not in {"all", "draft", "approved", "disabled"}:
        raise HTTPException(status_code=400, detail="Invalid skill status")
    return {"skills": list_skills(status)}


@router.post("/skills")
async def api_create_skill(req: SkillCreateRequest):
    try:
        return create_skill(req.name, req.description, req.triggers, req.steps, req.category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/skills/{skill_id}/disable")
async def api_disable_skill(skill_id: int):
    if not disable_skill(skill_id):
        raise HTTPException(status_code=404, detail="Skill not found or already disabled")
    return {"status": "disabled", "skill_id": skill_id}

@router.get("/notes")
async def api_list_notes(query: str = "", status: str = "active"):
    return {"notes": list_notes(query=query, status=status)}

@router.post("/notes")
async def api_create_note(req: NoteCreateRequest):
    return create_note(req.title, req.content, req.tags)

@router.patch("/notes/{note_id}")
async def api_update_note(note_id: int, req: NoteUpdateRequest):
    if req.status is not None and req.status not in {"active", "archived"}:
        raise HTTPException(status_code=400, detail="Invalid note status")
    note = update_note(note_id, req.title, req.content, req.tags, req.status)
    if not note: raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.post("/notes/{note_id}/extract")
async def api_extract_note_facts(note_id: int):
    results = await extract_note_facts(note_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Active note not found")
    return {"facts": results}

@router.get("/facts")
async def api_list_facts(query: str = "", category: str | None = None, status: str = "approved"):
    if status not in {"approved", "pending_approval", "rejected", "merged"}:
        raise HTTPException(status_code=400, detail="Invalid fact status")
    return {"facts": list_facts(query=query, category=category, status=status)}

@router.patch("/facts/{fact_id}")
async def api_update_fact(fact_id: int, req: FactUpdateRequest):
    if req.category is not None and req.category not in {"preference", "habit", "relationship", "project", "other"}:
        raise HTTPException(status_code=400, detail="Invalid fact category")
    fact = update_fact(fact_id, req.content, req.category, is_pinned=req.is_pinned)
    if not fact: raise HTTPException(status_code=404, detail="Fact not found or expired")
    return fact

@router.post("/facts/{fact_id}/confirm")
async def api_confirm_fact(fact_id: int):
    fact = confirm_fact(fact_id)
    if not fact: raise HTTPException(status_code=404, detail="Fact not found or inactive")
    return fact

@router.get("/search")
async def api_search_memory(query: str = Query(min_length=1, max_length=200), limit: int = Query(default=12, ge=1, le=50)):
    return {"results": search_memory(query, limit)}

class ConsolidateRequest(BaseModel):
    fact_ids: list[int]
    merged_content: str
    category: str

@router.post("/consolidation-suggestions")
async def api_get_consolidation_suggestions():
    try:
        # Use cached results from nightly scheduled job if available
        from backend.app.memory.memory_service import (
            get_cached_consolidation_suggestions,
            find_consolidation_candidates,
            set_consolidation_cache
        )
        cached, cached_at = get_cached_consolidation_suggestions()
        if cached and cached_at:
            return {"suggestions": cached, "cached_at": cached_at.isoformat()}
        # Fallback: compute on demand
        suggestions = await find_consolidation_candidates()
        set_consolidation_cache(suggestions)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consolidate")
async def api_consolidate_facts(req: ConsolidateRequest):
    try:
        if not req.fact_ids or len(req.fact_ids) < 2:
            raise HTTPException(status_code=400, detail="Must provide at least 2 fact IDs to consolidate.")
        new_id = consolidate_facts(req.fact_ids, req.merged_content, req.category)
        return {
            "status": "success",
            "message": f"Successfully consolidated facts into new fact #{new_id}",
            "new_fact_id": new_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FactValidityRequest(BaseModel):
    valid_to: str | None = None

@router.patch("/facts/{fact_id}/validity")
async def api_set_fact_validity(fact_id: int, req: FactValidityRequest):
    from backend.app.storage.db import get_db_connection
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_facts WHERE id = ?", (fact_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Fact {fact_id} not found.")
            cursor.execute(
                "UPDATE user_facts SET valid_to = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (req.valid_to, fact_id)
            )
            conn.commit()
        return {"status": "success", "message": f"Fact {fact_id} validity updated.", "valid_to": req.valid_to}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
