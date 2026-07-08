# Technical Notes

## Memory Retrieval Strategy

### Current approach: Naive LLM-based filtering (no embeddings)

The orchestrator retrieves relevant user facts via `get_relevant_facts(query)` in 
`memory_service.py`. The approach:

1. Fetch all approved facts from the `user_facts` SQLite table.
2. If total facts ≤ limit (default 5) → return all, skip LLM call entirely.
3. If total facts > limit → send the full list + user query to Ollama with a prompt 
   asking it to select the most relevant fact IDs. Parse the JSON response and filter.

**Why this tradeoff:**
- No vector store dependency (no Qdrant, no embedding model required beyond the main LLM).
- Works well while the facts count is small (< 50–100).
- Extra LLM call per request adds ~0.5–1s latency, acceptable for a personal assistant.

**When to migrate:**
- When approved facts exceed ~100, the full-list-to-LLM approach becomes inefficient 
  (context window waste, slower filtering). At that point, switch to embeddings-based 
  retrieval (e.g. `nomic-embed-text` + Qdrant or ChromaDB).

---

## Mem0 / Qdrant Integration — Replaced

The project previously used [Mem0](https://github.com/mem0ai/mem0) with a local Qdrant 
vector store (`qdrant_db/` directory) and `nomic-embed-text` embeddings for automatic 
memory extraction and retrieval.

**Why it was replaced:**
- The custom Memory Layer provides a **human-in-the-loop confirmation flow** 
  (approve/reject UI) that Mem0 doesn't support out of the box.
- Facts stored in SQLite (`user_facts` table) are directly tied to the interactive 
  graph visualization, relation builder, and the review queue in the frontend.
- Mem0's automatic extraction was too opaque — facts were added without user control, 
  leading to unreliable or duplicate entries.

**What was removed:**
- `backend/app/memory/mem0_client.py` — no longer imported (file kept for reference).
- `mem0ai` removed from `requirements.txt`.
- The Mem0 integration block in `orchestrator.py` (lines 478–503) was replaced with 
  the custom `get_relevant_facts()` call.

**What was kept:**
- The `qdrant_db/` directory and any Docker containers remain untouched — the user 
  will decide separately whether they are needed for other purposes.

---

## Background Fact Extraction

After the LLM produces a final text response in the orchestrator, a background 
`asyncio.create_task` fires `extract_facts_from_conversation()` with the 
user+assistant exchange. New facts are saved as `pending_approval` and appear in 
the review queue UI at `/memory` → "На подтверждение" tab. This does NOT block 
the response to the user.

---

## Fact Consolidation Strategy

### Semantic Clustering and Human-in-the-loop Merging

As user facts accumulate, semantic redundancy increases (e.g. "Не любит просыпаться рано" and "Не любит встречи до 10 утра"). Rather than doing automatic, potentially destructive merges, the system uses a **user-confirmed consolidation flow**:

1. **Candidate Discovery**: `find_consolidation_candidates()` scans all `approved` facts and sends them to the LLM. The LLM groups highly overlapping facts into clusters of 2+ entries and proposes a unified Russian phrasing (e.g. "Не любит утренние активности и встречи до 10 утра").
2. **Review Queue**: Suggestions are rendered in the "Консолидация" tab in the frontend. Users can edit the suggested wording and change the category before confirming.
3. **Execution (`/consolidate`)**:
   - Creates a new fact containing the edited merged text and sets its status to `approved`.
   - The old source facts are updated with a new status `"merged"`, and their `merged_into_id` column points to the new fact for auditing.
   - All external relationships (`fact_relations`) involving any of the old facts are re-bound to the new consolidated fact. Internal relations within the merged group are removed.
   - Merged facts are hidden from the primary memory graph and prompt retrieval by default.

**Why this approach was chosen:**
- **Control**: Memory is the base of the assistant's behavior. Auto-merges can corrupt nuances of user data without user awareness.
- **Traceability**: Retaining the old records with the `"merged"` status and a reference link (`merged_into_id`) leaves a clean audit trail.
- **Relational Integrity**: Re-binding the D3 graph relations ensures the Obsidian-style graph remains fully connected and meaningful.

