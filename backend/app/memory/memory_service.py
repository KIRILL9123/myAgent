import asyncio
import json
import logging
from datetime import datetime as _dt
from backend.app.core.execution_mode import is_dry_run
from backend.app.storage.db import get_db_connection
from typing import Any

logger = logging.getLogger(__name__)

# ─── Embedding threshold: log a warning when fact count exceeds this ─────────
EMBEDDING_THRESHOLD = 100
# TODO: Once fact count exceeds EMBEDDING_THRESHOLD, migrate database storage
# to a vector DB (e.g. Qdrant) and compute embeddings using a lightweight model (e.g. sentence-transformers).

_RUSSIAN_STOPWORDS = {
    "как", "для", "что", "его", "это", "там", "где", "или", "она",
    "они", "оно", "при", "уже", "еще", "был", "все", "той", "тот", "эту"
}

AUTO_APPROVE_CATEGORIES = {"preference", "habit", "project"}
AUTO_APPROVE_CONFIDENCE = 0.90

def save_pending_fact(content: str, category: str, confidence: float, source_conversation_id: int | None = None,
                      source_type: str = "llm_extraction", provenance: dict[str, Any] | None = None) -> int:
    if is_dry_run():
        return -1

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_facts (content, category, source_conversation_id, confidence, status,
                                    source_type, last_confirmed_at, valid_from, approval_mode, provenance_json)
            VALUES (?, ?, ?, ?, 'pending_approval', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'pending_review', ?)
            """,
            (content, category, source_conversation_id, confidence, source_type, json.dumps(provenance or {}, ensure_ascii=False))
        )
        new_id = cursor.lastrowid
        conn.commit()
    return new_id

def save_extracted_fact(content: str, category: str, confidence: float, source_conversation_id: int | None = None,
                        source_type: str = "chat", provenance: dict[str, Any] | None = None) -> tuple[int, str]:
    """Save safe high-confidence personal facts directly; route everything else to review."""
    auto_approved = confidence >= AUTO_APPROVE_CONFIDENCE and category in AUTO_APPROVE_CATEGORIES
    status = "approved" if auto_approved else "pending_approval"
    approval_mode = "auto_high_confidence" if auto_approved else "pending_review"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO user_facts (content, category, source_conversation_id, confidence, status,
                                         source_type, last_confirmed_at, valid_from, approval_mode, provenance_json)
               VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? = 'approved' THEN CURRENT_TIMESTAMP ELSE NULL END,
                       CURRENT_TIMESTAMP, ?, ?)""",
            (content, category, source_conversation_id, confidence, status, source_type, status,
             approval_mode, json.dumps(provenance or {}, ensure_ascii=False)),
        )
        fact_id = cursor.lastrowid
        conn.commit()
    _sync_memory_search_index()
    clear_consolidation_cache()
    return fact_id, status

def _sync_memory_search_index() -> None:
    """Small local index; rebuilding is inexpensive at the current personal scale."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_search")
        cursor.execute("SELECT id, title, content, tags_json FROM memory_notes WHERE status = 'active'")
        for note_id, title, content, tags_json in cursor.fetchall():
            cursor.execute("INSERT INTO memory_search (item_type, item_id, title, content, tags) VALUES ('note', ?, ?, ?, ?)",
                           (str(note_id), title, content, tags_json or ""))
        cursor.execute("SELECT id, content, category FROM user_facts WHERE status = 'approved' AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)")
        for fact_id, content, category in cursor.fetchall():
            cursor.execute("INSERT INTO memory_search (item_type, item_id, title, content, tags) VALUES ('fact', ?, ?, ?, ?)",
                           (str(fact_id), category, content, category))
        conn.commit()

def _fact_dict(row: tuple) -> dict[str, Any]:
    keys = ("id", "content", "category", "confidence", "status", "source_conversation_id", "created_at", "updated_at",
            "last_confirmed_at", "valid_from", "valid_to", "source_type", "approval_mode", "provenance_json", "is_pinned")
    item = dict(zip(keys, row))
    try:
        item["provenance"] = json.loads(item.pop("provenance_json") or "{}")
    except json.JSONDecodeError:
        item["provenance"] = {}
    item["is_pinned"] = bool(item["is_pinned"])
    return item

def list_facts(query: str = "", category: str | None = None, status: str = "approved") -> list[dict[str, Any]]:
    clauses, params = ["status = ?"], [status]
    if status == "approved":
        clauses.append("(valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)")
    if category:
        clauses.append("category = ?"); params.append(category)
    if query.strip():
        clauses.append("content LIKE ?"); params.append(f"%{query.strip()}%")
    sql = "SELECT id, content, category, confidence, status, source_conversation_id, created_at, updated_at, last_confirmed_at, valid_from, valid_to, source_type, approval_mode, provenance_json, is_pinned FROM user_facts WHERE " + " AND ".join(clauses) + " ORDER BY is_pinned DESC, updated_at DESC, id DESC"
    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_fact_dict(row) for row in rows]

def update_fact(fact_id: int, content: str | None = None, category: str | None = None, valid_to: str | None = None,
                is_pinned: bool | None = None) -> dict[str, Any] | None:
    changes: list[str] = ["updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = []
    if content is not None: changes.append("content = ?"); params.append(content.strip())
    if category is not None: changes.append("category = ?"); params.append(category)
    if valid_to is not None: changes.append("valid_to = ?"); params.append(valid_to or None)
    if is_pinned is not None: changes.append("is_pinned = ?"); params.append(int(is_pinned))
    params.append(fact_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(); cursor.execute(f"UPDATE user_facts SET {', '.join(changes)} WHERE id = ?", params)
        if cursor.rowcount == 0: return None
        conn.commit()
    _sync_memory_search_index()
    return next((item for item in list_facts(status="approved") if item["id"] == fact_id), None)

def confirm_fact(fact_id: int) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        cursor = conn.cursor(); cursor.execute("UPDATE user_facts SET last_confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, approval_mode = 'user_confirmed' WHERE id = ? AND status = 'approved'", (fact_id,))
        if cursor.rowcount == 0: return None
        conn.commit()
    return next((item for item in list_facts(status="approved") if item["id"] == fact_id), None)

def create_note(title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
    clean_tags = sorted({tag.strip().lower() for tag in (tags or []) if tag.strip()})
    with get_db_connection() as conn:
        cursor = conn.cursor(); cursor.execute("INSERT INTO memory_notes (title, content, tags_json) VALUES (?, ?, ?)", (title.strip(), content.strip(), json.dumps(clean_tags, ensure_ascii=False)))
        note_id = cursor.lastrowid; conn.commit()
    _sync_memory_search_index()
    return get_note(note_id) or {}

def get_note(note_id: int) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute("SELECT id, title, content, tags_json, status, created_at, updated_at FROM memory_notes WHERE id = ?", (note_id,)).fetchone()
    return _note_dict(row) if row else None

def _note_dict(row: tuple) -> dict[str, Any]:
    try: tags = json.loads(row[3] or "[]")
    except json.JSONDecodeError: tags = []
    return {"id": row[0], "title": row[1], "content": row[2], "tags": tags, "status": row[4], "created_at": row[5], "updated_at": row[6]}

def list_notes(query: str = "", status: str = "active") -> list[dict[str, Any]]:
    clauses, params = ["status = ?"], [status]
    if query.strip(): clauses.append("(title LIKE ? OR content LIKE ? OR tags_json LIKE ?)"); params.extend([f"%{query.strip()}%"] * 3)
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, title, content, tags_json, status, created_at, updated_at FROM memory_notes WHERE " + " AND ".join(clauses) + " ORDER BY updated_at DESC, id DESC", params).fetchall()
    return [_note_dict(row) for row in rows]

def update_note(note_id: int, title: str | None = None, content: str | None = None, tags: list[str] | None = None, status: str | None = None) -> dict[str, Any] | None:
    changes, params = ["updated_at = CURRENT_TIMESTAMP"], []
    if title is not None: changes.append("title = ?"); params.append(title.strip())
    if content is not None: changes.append("content = ?"); params.append(content.strip())
    if tags is not None: changes.append("tags_json = ?"); params.append(json.dumps(sorted({tag.strip().lower() for tag in tags if tag.strip()}), ensure_ascii=False))
    if status is not None: changes.append("status = ?"); params.append(status)
    params.append(note_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(); cursor.execute(f"UPDATE memory_notes SET {', '.join(changes)} WHERE id = ?", params)
        if cursor.rowcount == 0: return None
        conn.commit()
    _sync_memory_search_index()
    return get_note(note_id)

async def extract_note_facts(note_id: int) -> list[dict[str, Any]] | None:
    note = get_note(note_id)
    if not note or note["status"] != "active":
        return None
    from backend.app.memory.fact_extractor import extract_facts_from_conversation
    text = f"User note title: {note['title']}\nUser note: {note['content']}"
    return await extract_facts_from_conversation(
        text,
        source_type="manual_note",
        provenance={"note_id": note_id, "note_title": note["title"]},
    )

def get_memory_overview() -> dict[str, int]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        return {"notes": cursor.execute("SELECT COUNT(*) FROM memory_notes WHERE status = 'active'").fetchone()[0],
                "approved_facts": cursor.execute("SELECT COUNT(*) FROM user_facts WHERE status = 'approved' AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP)").fetchone()[0],
                "pending_facts": cursor.execute("SELECT COUNT(*) FROM user_facts WHERE status = 'pending_approval'").fetchone()[0],
                "stale_facts": cursor.execute("SELECT COUNT(*) FROM user_facts WHERE status = 'approved' AND last_confirmed_at IS NOT NULL AND last_confirmed_at < datetime('now', '-90 days')").fetchone()[0]}

def search_memory(query: str, limit: int = 12) -> list[dict[str, Any]]:
    terms = [term.replace('"', '') for term in query.split() if term.strip()]
    if not terms: return []
    _sync_memory_search_index()
    expression = " OR ".join(f'"{term}"' for term in terms)
    with get_db_connection() as conn:
        rows = conn.execute("SELECT item_type, item_id FROM memory_search WHERE memory_search MATCH ? LIMIT ?", (expression, limit)).fetchall()
    facts = {item["id"]: item for item in list_facts(status="approved")}
    notes = {item["id"]: item for item in list_notes()}
    results = []
    for kind, item_id in rows:
        item = facts.get(int(item_id)) if kind == "fact" else notes.get(int(item_id))
        if item:
            results.append({"type": kind, "item": item})
    return results

async def get_relevant_memory(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return compact, source-aware memory for the chat context."""
    results = search_memory(query, limit=limit)
    if results:
        return results[:limit]
    # Preserve the existing stemming/LLM fact path when FTS has no lexical hit.
    return [{"type": "fact", "item": item} for item in await get_relevant_facts(query, limit=limit)]

def _row_to_fact(r: tuple, include_status: bool = False) -> dict[str, Any]:
    fact = {
        "id": r[0],
        "content": r[1],
        "category": r[2],
        "source_conversation_id": r[3],
        "confidence": r[4],
        "created_at": r[5],
        "updated_at": r[6],
    }
    if include_status and len(r) > 7:
        fact["status"] = r[7]
    _offset = 1 if include_status else 0
    if len(r) > 7 + _offset:
        fact["last_confirmed_at"] = r[7 + _offset]
    if len(r) > 8 + _offset:
        fact["valid_from"] = r[8 + _offset]
    if len(r) > 9 + _offset:
        fact["valid_to"] = r[9 + _offset]
    if len(r) > 10 + _offset:
        fact["source_type"] = r[10 + _offset] if r[10 + _offset] is not None else "unknown"
    return fact

def get_pending_facts() -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, category, source_conversation_id, confidence, created_at, updated_at FROM user_facts WHERE status = 'pending_approval' ORDER BY id DESC"
        )
        rows = cursor.fetchall()
    return [_row_to_fact(r) for r in rows]

def get_approved_facts() -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, category, source_conversation_id, confidence, "
            "created_at, updated_at, last_confirmed_at, valid_from, valid_to, source_type "
            "FROM user_facts WHERE status = 'approved' "
            "AND (valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP) "
            "ORDER BY id DESC"
        )
        rows = cursor.fetchall()
    return [_row_to_fact(r) for r in rows]

def get_all_facts(status: str | None = None) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
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
    return [_row_to_fact(r, include_status=True) for r in rows]

def update_fact_timestamp(fact_id: int):
    if is_dry_run():
        return

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_facts SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (fact_id,)
        )
        conn.commit()

async def approve_fact(fact_id: int) -> bool:
    # 1. Fetch the fact to approve
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, category, source_conversation_id, confidence, status FROM user_facts WHERE id = ?",
            (fact_id,)
        )
        row = cursor.fetchone()
        if not row:
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
            return False

        if is_dry_run():
            return True
            
        # 2. Update status to approved
        cursor.execute(
            "UPDATE user_facts SET status = 'approved', updated_at = CURRENT_TIMESTAMP, last_confirmed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (fact_id,)
        )
        conn.commit()
    
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
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status FROM user_facts WHERE id = ?",
            (fact_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False
            
        if row[1] != "pending_approval":
            return False

        if is_dry_run():
            return True
            
        cursor.execute(
            "UPDATE user_facts SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (fact_id,)
        )
        conn.commit()
    clear_consolidation_cache()
    return True

def save_relation(fact_a_id: int, fact_b_id: int, relation_type: str) -> bool:
    if is_dry_run():
        return True

    with get_db_connection() as conn:
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
            return True
    return False

def get_graph_data() -> dict[str, list[dict[str, Any]]]:
    with get_db_connection() as conn:
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
        
    return {"nodes": nodes, "edges": edges}

def get_isolated_approved_facts() -> list[dict[str, Any]]:
    with get_db_connection() as conn:
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
    from backend.app.memory.relation_builder import suggest_relations

    async def _process_one(fact: dict) -> int:
        other_facts = [f for f in all_approved if f["id"] != fact["id"]]
        if not other_facts:
            return 0
        try:
            suggestions = await suggest_relations(fact, other_facts)
            added = 0
            for sug in suggestions:
                fact_b_id = sug.get("fact_b_id")
                relation_type = sug.get("relation_type")
                if fact_b_id and relation_type:
                    if save_relation(fact["id"], fact_b_id, relation_type):
                        added += 1
            return added
        except Exception as e:
            print(f"[MemoryService] Error during backfill suggest_relations for fact #{fact['id']}: {e}")
            return 0

    results = await asyncio.gather(*[_process_one(f) for f in isolated_facts], return_exceptions=True)
    return sum(r for r in results if isinstance(r, int))

def _filter_facts_by_keyword(approved: list[dict], query: str) -> list[dict]:
    import re
    # Regex split to get alphanumeric words in lowercase
    query_words = re.findall(r'[a-zа-яё0-9]+', query.lower())
    query_words = [w for w in query_words if len(w) >= 3 and w not in _RUSSIAN_STOPWORDS]
    if not query_words:
        return []

    # Get stems: first 5 characters of each word, plus full word fallback
    def get_stems_and_words(words_list):
        result = set()
        for w in words_list:
            result.add(w) # fallback: full word
            if len(w) >= 5:
                result.add(w[:5]) # first 5 chars
            elif len(w) >= 4:
                result.add(w[:4]) # first 4 chars
        return result

    query_targets = get_stems_and_words(query_words)
    matched_facts = []

    for fact in approved:
        content_lower = fact["content"].lower()
        fact_words = re.findall(r'[a-zа-яё0-9]+', content_lower)
        fact_words = [w for w in fact_words if len(w) >= 3 and w not in _RUSSIAN_STOPWORDS]
        fact_targets = get_stems_and_words(fact_words)

        overlap = query_targets.intersection(fact_targets)
        if overlap:
            matched_facts.append((len(overlap), fact))

    # Sort by overlap score descending
    matched_facts.sort(key=lambda x: x[0], reverse=True)
    return [fact for _, fact in matched_facts]


async def get_relevant_facts(query: str, limit: int = 5) -> list[dict]:
    """
    Retrieve approved facts relevant to the user's query.
    
    Strategy:
    - Step 1: Filter facts by keyword (fast stem/exact match).
    - Step 2: If candidates count <= limit, return them directly (skip LLM call).
    - Step 3: If candidates count > limit, ask LLM to pick the most relevant IDs from candidates.
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
    
    # 1. Apply fast keyword matching filter
    candidates = _filter_facts_by_keyword(approved, query)
    
    if not candidates:
        print(f"[MEMORY] No keyword overlap found, returning 0 facts and skipping LLM filter")
        return []
        
    # Shortcut: if we have few candidates, just return them — no need for LLM filtering
    if len(candidates) <= limit:
        print(f"[MEMORY] Returning all {len(candidates)} candidate facts (≤ limit {limit}), skipping LLM filter")
        return candidates
    
    # Build a numbered list for the LLM from candidates
    facts_list_str = "\n".join([
        f"- ID: {f['id']}, Content: \"{f['content']}\", Category: {f['category']}"
        for f in candidates
    ])
    
    filter_prompt = (
        f"Given these known facts about a user:\n{facts_list_str}\n\n"
        f"The user just sent this message: \"{query}\"\n\n"
        f"Select up to {limit} facts that are most relevant to this message. "
        f"Return ONLY a JSON object in this exact format:\n"
        f'{{\"fact_ids\": [1, 2, 3]}}\n'
        f"If no facts are relevant, return: {{\"fact_ids\": []}}"
    )
    
    from backend.app.agent.llm import chat as chat_with_ollama
    import json
    
    response = await chat_with_ollama(
        [{"role": "system", "content": filter_prompt}],
        response_format="json", role="extractor"
    )

    if "error" in response:
        print(f"[MEMORY] LLM filter error, falling back to candidates limit: {response['error']}")
        return candidates[:limit]
    
    content_str = response.get("message", {}).get("content", "")
    try:
        data = json.loads(content_str)
        selected_ids = data.get("fact_ids", [])
        if not isinstance(selected_ids, list):
            selected_ids = []
        # Convert to int safely
        selected_ids = [int(x) for x in selected_ids if x is not None]
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[MEMORY] Failed to parse LLM filter response: {e}, falling back to candidates limit")
        return candidates[:limit]
    
    if not selected_ids:
        # LLM found nothing relevant — return empty
        return []
    
    # Filter candidate facts by selected IDs, preserving order
    selected_id_set = set(selected_ids)
    relevant = [f for f in candidates if f["id"] in selected_id_set]
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
    
    from backend.app.agent.llm import chat as chat_with_ollama
    import json
    
    response = await chat_with_ollama(messages, response_format="json", role="extractor")
    if response.get("status") == "error" or "error" in response:
        print(f"[MemoryService] Consolidation LLM Error: {response.get('message', response.get('error'))}")
        return []
        
    message = response.get("message", {})
    if not isinstance(message, dict):
        return []
    content_str = message.get("content", "")
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
    if is_dry_run():
        return -1

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_facts (content, category, confidence, status,
                                    source_type, last_confirmed_at, valid_from)
            VALUES (?, ?, ?, 'approved', 'manual_consolidation', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (content, category, confidence)
        )
        new_id = cursor.lastrowid
        conn.commit()
    return new_id

def mark_facts_as_merged(fact_ids: list[int], merged_into_id: int):
    if is_dry_run():
        return

    with get_db_connection() as conn:
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

def consolidate_facts(fact_ids: list[int], merged_content: str, category: str) -> int:
    if is_dry_run():
        return -1

    # 1. Create new approved fact
    new_id = save_approved_fact(merged_content, category, 0.95)
    
    # 2. Re-bind relations to the new fact
    with get_db_connection() as conn:
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

def set_consolidation_cache(suggestions: list[dict]):
    """Set cached consolidation suggestions and update the timestamp."""
    global _consolidation_cache, _consolidation_cache_timestamp
    _consolidation_cache = suggestions
    _consolidation_cache_timestamp = _dt.now()

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
