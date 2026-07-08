import logging
from datetime import datetime as _dt
from backend.app.storage.db import _get_connection
from typing import Any

logger = logging.getLogger(__name__)

# ─── Embedding threshold: log a warning when fact count exceeds this ─────────
EMBEDDING_THRESHOLD = 100

def save_pending_fact(content: str, category: str, confidence: float, source_conversation_id: int | None = None) -> int:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_facts (content, category, source_conversation_id, confidence, status)
        VALUES (?, ?, ?, ?, 'pending_approval')
        """,
        (content, category, source_conversation_id, confidence)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_pending_facts() -> list[dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, category, source_conversation_id, confidence, created_at, updated_at FROM user_facts WHERE status = 'pending_approval' ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "content": r[1],
            "category": r[2],
            "source_conversation_id": r[3],
            "confidence": r[4],
            "created_at": r[5],
            "updated_at": r[6]
        }
        for r in rows
    ]

def get_approved_facts() -> list[dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, category, source_conversation_id, confidence, created_at, updated_at FROM user_facts WHERE status = 'approved' ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "content": r[1],
            "category": r[2],
            "source_conversation_id": r[3],
            "confidence": r[4],
            "created_at": r[5],
            "updated_at": r[6]
        }
        for r in rows
    ]

def get_all_facts(status: str | None = None) -> list[dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "SELECT id, content, category, source_conversation_id, confidence, created_at, updated_at, status FROM user_facts WHERE status = ? ORDER BY id DESC",
            (status,)
        )
    else:
        cursor.execute(
            "SELECT id, content, category, source_conversation_id, confidence, created_at, updated_at, status FROM user_facts WHERE status != 'merged' ORDER BY id DESC"
        )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "content": r[1],
            "category": r[2],
            "source_conversation_id": r[3],
            "confidence": r[4],
            "created_at": r[5],
            "updated_at": r[6],
            "status": r[7]
        }
        for r in rows
    ]

def update_fact_timestamp(fact_id: int):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE user_facts SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (fact_id,)
    )
    conn.commit()
    conn.close()

async def approve_fact(fact_id: int) -> bool:
    # 1. Fetch the fact to approve
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, category, source_conversation_id, confidence, status FROM user_facts WHERE id = ?",
        (fact_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    fact = {
        "id": row[0],
        "content": row[1],
        "category": row[2],
        "source_conversation_id": row[3],
        "confidence": row[4],
        "status": row[5]
    }
    
    if fact["status"] != "pending_approval":
        # Already approved or rejected
        conn.close()
        return False
        
    # 2. Update status to approved
    cursor.execute(
        "UPDATE user_facts SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (fact_id,)
    )
    conn.commit()
    conn.close()
    
    # 3. Retrieve all other approved facts
    existing_facts = get_approved_facts()
    # Filter out the newly approved fact itself (it shouldn't link to itself)
    other_approved_facts = [f for f in existing_facts if f["id"] != fact_id]
    
    # 4. Suggest relationships
    if other_approved_facts:
        from backend.app.memory.relation_builder import suggest_relations
        try:
            suggestions = await suggest_relations(fact, other_approved_facts)
            for sug in suggestions:
                fact_b_id = sug.get("fact_b_id")
                relation_type = sug.get("relation_type")
                if fact_b_id and relation_type:
                    save_relation(fact_id, fact_b_id, relation_type)
        except Exception as e:
            # Log relation building error but don't fail the approval itself
            print(f"[MemoryService] Error suggesting relations: {e}")
            
    clear_consolidation_cache()
    return True

def reject_fact(fact_id: int) -> bool:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, status FROM user_facts WHERE id = ?",
        (fact_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    if row[1] != "pending_approval":
        conn.close()
        return False
        
    cursor.execute(
        "UPDATE user_facts SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (fact_id,)
    )
    conn.commit()
    conn.close()
    clear_consolidation_cache()
    return True

def save_relation(fact_a_id: int, fact_b_id: int, relation_type: str):
    conn = _get_connection()
    cursor = conn.cursor()
    # Check if relation already exists in either direction
    cursor.execute(
        """
        SELECT 1 FROM fact_relations 
        WHERE (fact_a_id = ? AND fact_b_id = ?) 
           OR (fact_a_id = ? AND fact_b_id = ?)
        """,
        (fact_a_id, fact_b_id, fact_b_id, fact_a_id)
    )
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO fact_relations (fact_a_id, fact_b_id, relation_type) VALUES (?, ?, ?)",
            (fact_a_id, fact_b_id, relation_type)
        )
        conn.commit()
    conn.close()

def get_graph_data() -> dict[str, list[dict[str, Any]]]:
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Nodes (only approved facts)
    cursor.execute(
        "SELECT id, content, category, confidence FROM user_facts WHERE status = 'approved'"
    )
    nodes = [{"id": r[0], "content": r[1], "category": r[2], "confidence": r[3]} for r in cursor.fetchall()]
    
    # Edges (relations between approved facts)
    cursor.execute(
        """
        SELECT r.fact_a_id, r.fact_b_id, r.relation_type 
        FROM fact_relations r
        JOIN user_facts fa ON r.fact_a_id = fa.id
        JOIN user_facts fb ON r.fact_b_id = fb.id
        WHERE fa.status = 'approved' AND fb.status = 'approved'
        """
    )
    edges = [{"source": r[0], "target": r[1], "relation_type": r[2]} for r in cursor.fetchall()]
    
    conn.close()
    return {"nodes": nodes, "edges": edges}

def get_isolated_approved_facts() -> list[dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, content, category, source_conversation_id, confidence, created_at, updated_at 
        FROM user_facts 
        WHERE status = 'approved'
          AND id NOT IN (SELECT fact_a_id FROM fact_relations)
          AND id NOT IN (SELECT fact_b_id FROM fact_relations)
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "content": r[1],
            "category": r[2],
            "source_conversation_id": r[3],
            "confidence": r[4],
            "created_at": r[5],
            "updated_at": r[6]
        }
        for r in rows
    ]

async def backfill_isolated_relations() -> int:
    isolated_facts = get_isolated_approved_facts()
    if not isolated_facts:
        return 0
        
    all_approved = get_approved_facts()
    relations_added = 0
    from backend.app.memory.relation_builder import suggest_relations
    
    for fact in isolated_facts:
        other_facts = [f for f in all_approved if f["id"] != fact["id"]]
        if not other_facts:
            continue
            
        try:
            suggestions = await suggest_relations(fact, other_facts)
            for sug in suggestions:
                fact_b_id = sug.get("fact_b_id")
                relation_type = sug.get("relation_type")
                if fact_b_id and relation_type:
                    conn = _get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT 1 FROM fact_relations 
                        WHERE (fact_a_id = ? AND fact_b_id = ?) 
                           OR (fact_a_id = ? AND fact_b_id = ?)
                        """,
                        (fact["id"], fact_b_id, fact_b_id, fact["id"])
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO fact_relations (fact_a_id, fact_b_id, relation_type) VALUES (?, ?, ?)",
                            (fact["id"], fact_b_id, relation_type)
                        )
                        conn.commit()
                        relations_added += 1
                    conn.close()
        except Exception as e:
            print(f"[MemoryService] Error during backfill suggest_relations for fact #{fact['id']}: {e}")
            
    return relations_added

async def get_relevant_facts(query: str, limit: int = 5) -> list[dict]:
    """
    Retrieve approved facts relevant to the user's query.
    
    Strategy (naive LLM-based, no embeddings):
    - If total approved facts ≤ limit → return all (skip LLM call)
    - If total approved facts > limit → ask LLM to pick the most relevant IDs
    
    This is an intentional compromise while the facts count is small (<50-100).
    """
    approved = get_approved_facts()
    
    if not approved:
        return []
    
    # ── Embedding threshold warning ──
    if len(approved) > EMBEDDING_THRESHOLD:
        logger.warning(
            f"Fact count ({len(approved)}) exceeded {EMBEDDING_THRESHOLD}, "
            "consider switching to embeddings-based retrieval"
        )
    
    # Shortcut: if we have few facts, just return all — no need for LLM filtering
    if len(approved) <= limit:
        print(f"[MEMORY] Returning all {len(approved)} approved facts (≤ limit {limit}), skipping LLM filter")
        return approved
    
    # Build a numbered list for the LLM
    facts_list_str = "\n".join([
        f"- ID: {f['id']}, Content: \"{f['content']}\", Category: {f['category']}"
        for f in approved
    ])
    
    filter_prompt = (
        f"Given these known facts about a user:\n{facts_list_str}\n\n"
        f"The user just sent this message: \"{query}\"\n\n"
        f"Select up to {limit} facts that are most relevant to this message. "
        f"Return ONLY a JSON object in this exact format:\n"
        f'{{\"fact_ids\": [1, 2, 3]}}\n'
        f"If no facts are relevant, return: {{\"fact_ids\": []}}"
    )
    
    from backend.app.agent.llm_client import chat_with_ollama
    import json
    
    response = await chat_with_ollama(
        [{"role": "system", "content": filter_prompt}],
        response_format="json"
    )
    
    if "error" in response:
        print(f"[MEMORY] LLM filter error, falling back to all facts: {response['error']}")
        return approved[:limit]
    
    content_str = response.get("message", {}).get("content", "")
    try:
        data = json.loads(content_str)
        selected_ids = data.get("fact_ids", [])
        if not isinstance(selected_ids, list):
            selected_ids = []
        # Convert to int safely
        selected_ids = [int(x) for x in selected_ids if x is not None]
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[MEMORY] Failed to parse LLM filter response: {e}, falling back to all facts")
        return approved[:limit]
    
    if not selected_ids:
        # LLM found nothing relevant — return empty
        return []
    
    # Filter approved facts by selected IDs, preserving order
    selected_id_set = set(selected_ids)
    relevant = [f for f in approved if f["id"] in selected_id_set]
    return relevant

CONSOLIDATION_PROMPT = """You are a semantic consolidation assistant. Analyze this list of user facts and group facts that contain overlapping, redundant, or semantically similar information that can be merged into a single, more concise and consolidated fact.

Do not group facts that are merely related (e.g., 'plays football' and 'likes beer'). Group only those that express the same or highly overlapping user habits, preferences, relationships, or details with different wordings or levels of detail (e.g., 'does not like early mornings', 'hates waking up before 9 AM', 'no meetings before 10 AM').

Return a JSON array of consolidation suggestions. Each suggestion must have:
- 'fact_ids': array of integers (the IDs of the facts to merge)
- 'suggested_merged_content': a single, clear, consolidated fact in Russian (e.g., 'Не любит утренние активности и встречи до 10-11 утра')
- 'category': the category for the new fact (must be one of: preference, habit, relationship, project, other)

Response format MUST be a valid JSON array at the top level:
[
  {"fact_ids": [1, 2], "suggested_merged_content": "...", "category": "..."}
]
If there are no facts that should be merged, return an empty array: []"""

async def find_consolidation_candidates() -> list[dict]:
    approved = get_approved_facts()
    if len(approved) < 2:
        return []
        
    facts_str = "\n".join([
        f"- ID: {f['id']}, Content: '{f['content']}', Category: '{f['category']}'"
        for f in approved
    ])
    
    messages = [
        {"role": "system", "content": CONSOLIDATION_PROMPT},
        {"role": "user", "content": f"Here is the list of user facts:\n{facts_str}"}
    ]
    
    from backend.app.agent.llm_client import chat_with_ollama
    import json
    
    response = await chat_with_ollama(messages, response_format="json")
    if "error" in response:
        print(f"[MemoryService] Consolidation LLM Error: {response['error']}")
        return []
        
    content_str = response.get("message", {}).get("content", "")
    if not content_str:
        return []
        
    try:
        data = json.loads(content_str)
        if isinstance(data, dict):
            data = [data]
            
        if not isinstance(data, list):
            return []
            
        valid_suggestions = []
        for item in data:
            ids = item.get("fact_ids", [])
            content = item.get("suggested_merged_content")
            category = item.get("category")
            
            # Ensure it is a valid list of 2+ fact IDs
            if isinstance(ids, list) and len(ids) >= 2 and content and category:
                # Resolve the actual source fact objects to return details to the frontend
                source_facts = [f for f in approved if f["id"] in ids]
                if len(source_facts) >= 2:
                    valid_suggestions.append({
                        "fact_ids": [f["id"] for f in source_facts],
                        "source_facts": source_facts,
                        "suggested_merged_content": content,
                        "category": category
                    })
        return valid_suggestions
    except Exception as e:
        print(f"[MemoryService] Failed to parse consolidation suggestions: {e}")
        return []

def save_approved_fact(content: str, category: str, confidence: float) -> int:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_facts (content, category, confidence, status)
        VALUES (?, ?, ?, 'approved')
        """,
        (content, category, confidence)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def mark_facts_as_merged(fact_ids: list[int], merged_into_id: int):
    conn = _get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(fact_ids))
    cursor.execute(
        f"""
        UPDATE user_facts 
        SET status = 'merged', merged_into_id = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id IN ({placeholders})
        """,
        [merged_into_id] + fact_ids
    )
    conn.commit()
    conn.close()

def consolidate_facts(fact_ids: list[int], merged_content: str, category: str) -> int:
    # 1. Create new approved fact
    new_id = save_approved_fact(merged_content, category, 0.95)
    
    # 2. Re-bind relations to the new fact
    conn = _get_connection()
    cursor = conn.cursor()
    
    placeholders = ",".join(["?"] * len(fact_ids))
    # Fetch all relations involving any of the old facts
    cursor.execute(
        f"""
        SELECT fact_a_id, fact_b_id, relation_type FROM fact_relations
        WHERE fact_a_id IN ({placeholders}) OR fact_b_id IN ({placeholders})
        """,
        fact_ids + fact_ids
    )
    relations = cursor.fetchall()
    
    for fact_a, fact_b, rel_type in relations:
        other_id = None
        if fact_a in fact_ids and fact_b not in fact_ids:
            other_id = fact_b
        elif fact_b in fact_ids and fact_a not in fact_ids:
            other_id = fact_a
            
        if other_id is not None:
            # Re-link new_id with other_id
            from backend.app.memory.memory_service import save_relation
            save_relation(new_id, other_id, rel_type)
            
    # 3. Delete old relations involving these merged facts to clean up the DB
    cursor.execute(
        f"""
        DELETE FROM fact_relations
        WHERE fact_a_id IN ({placeholders}) OR fact_b_id IN ({placeholders})
        """,
        fact_ids + fact_ids
    )
    conn.commit()
    conn.close()
    
    # 4. Mark old facts as merged and set merged_into_id
    mark_facts_as_merged(fact_ids, new_id)
    
    clear_consolidation_cache()
    return new_id


# ─── Consolidation cache for scheduled pre-computation ──────────────────────
_consolidation_cache: list[dict] = []
_consolidation_cache_timestamp: _dt | None = None

def clear_consolidation_cache():
    """Clear cached consolidation suggestions when memory state changes."""
    global _consolidation_cache, _consolidation_cache_timestamp
    _consolidation_cache = []
    _consolidation_cache_timestamp = None

def get_cached_consolidation_suggestions() -> tuple[list[dict], _dt | None]:
    """Return cached consolidation suggestions and the time they were computed."""
    return _consolidation_cache, _consolidation_cache_timestamp

async def run_scheduled_consolidation():
    """
    Called by APScheduler at 3:00 AM daily.
    Pre-computes consolidation candidates and caches them so the UI tab
    loads instantly in the morning.
    """
    global _consolidation_cache, _consolidation_cache_timestamp
    try:
        suggestions = await find_consolidation_candidates()
        _consolidation_cache = suggestions
        _consolidation_cache_timestamp = _dt.now()
        if suggestions:
            logger.info(
                f"[CONSOLIDATION] Scheduled run found {len(suggestions)} consolidation candidate(s)."
            )
        else:
            logger.info("[CONSOLIDATION] Scheduled run: no consolidation candidates found.")
    except Exception as e:
        logger.error(f"[CONSOLIDATION] Scheduled consolidation failed: {e}")
