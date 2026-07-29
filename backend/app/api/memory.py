from fastapi import APIRouter, HTTPException
from backend.app.memory.memory_service import (
    get_pending_facts,
    approve_fact,
    reject_fact,
    get_graph_data,
    backfill_isolated_relations
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

from pydantic import BaseModel
from backend.app.memory.memory_service import find_consolidation_candidates, consolidate_facts

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
