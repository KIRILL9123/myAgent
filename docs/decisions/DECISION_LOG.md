# Technical Notes

## Reliability cycle closure — 2026-08-05

The bounded hardening cycle is closed. The release gate remains the required
baseline, and `backend/tests/test_cross_domain_integration.py` now proves the
local end-to-end projection path on a temporary SQLite database: Tool Registry
creates a task, calendar event, and finance transaction; Action Center reads the
task reminder; notification delivery returns a Telegram dry-run and records no
external send. Phone/LAN access is intentionally a separate deployment gate
until the placeholder API keys are replaced in the local environment.

The product slice is now implemented: Goals, Projects and Decision Journal use
the existing Tasks & Projects and Knowledge domains, with no new top-level
routes. Commitments remain the task source of truth and Chat/Telegram share the
central Tool Registry. The next cycle is projection polish in Today and Action
Center; no OCR or new autonomous domain is promoted ahead of it.

## Reliability hardening cycle — 2026-08-04

The full-project audit found a stable domain architecture but drift in a few
planning notes and several bounded runtime risks. Mira will finish documentation
reconciliation and safety hardening before opening Decision Journal, Projects, or
OCR. The first implementation slice enabled SQLite foreign keys, added a bounded
TTL to new pending confirmations, bounded Document Vault upload reads and cleanup,
fixed calendar notification bookkeeping, and made “New conversation” create a new
Chat session. CI parity with the local release gate and Finance/Action Center
presentation contracts remain open. Full evidence and acceptance criteria are in
[RELIABILITY_AUDIT_2026-08-04.md](RELIABILITY_AUDIT_2026-08-04.md).

## GitHub OSS audit refresh — 2026-08-04

The audit found useful references but no reason to replace Mira's current
domains or orchestration. Paperless-ngx is the strongest reference for the next
Document Vault OCR slice; Super Productivity/Vikunja are references for a future
project hierarchy; Actual Budget is a reference for future budgets. Khoj,
AppFlowy, LobeHub, Outline, Cal.com and Radicale remain non-adopted because of
license, scope, or duplication risk. Full comparison and the adapter boundary
are in [OSS_AUDIT_2026-08-04.md](OSS_AUDIT_2026-08-04.md).

## Open-source reuse boundary — 2026-08-04

The GitHub audit selected three immediate integrations: MarkItDown for the
Document Vault extractor, FullCalendar for the Calendar renderer, and Radix
Dialog for shared modal accessibility. Each is an adapter-level dependency;
Mira's SQLite ownership, FTS5 retrieval, domain services, approval flow,
conflict handling and local-first boundary remain unchanged. FullCalendar
packages stay on one `6.1.21` line and MarkItDown is pinned to `0.1.7` with
minimal document-format extras.

Tiptap was deliberately deferred because Memory notes are plain text and FTS5
indexes that text directly. A rich editor requires a storage-format and
sanitization decision first. The full provenance, license and removal record
is in [OSS_INTEGRATIONS.md](OSS_INTEGRATIONS.md).

## Subscription → Finance linking

Subscription tracking and financial forecasting remain separate approvals. An
active monthly EUR subscription can propose a recurring Finance template through
`SUBSCRIPTION_FINANCE_LINK`; the proposal is idempotent and cancellation only
deactivates future generation. The Finance domain now supports generic
currency-aware recurrence, but the Subscription link intentionally remains
limited to monthly EUR until its own billing-cycle and FX policy are approved.
See [SUBSCRIPTION_FINANCE_LINK.md](../design/SUBSCRIPTION_FINANCE_LINK.md).

## Finance currency and recurrence model — 2026-08-04

Finance now stores the original currency on every transaction and recurring
template, groups all totals by currency, and intentionally does not perform FX
conversion. Recurring templates support weekly, monthly, and yearly schedules;
the forecast is a read-only three-calendar-month projection. This resolves the
old “generic recurrence/currency is future work” note without expanding the
domain into accounts, budgets, or exchange-rate history.

The GitHub audit used Firefly III and Actual Budget as product references and
reviewed `python-dateutil` and `rrule.js` for recurrence scope. No recurrence
dependency was added because the current personal workflow needs only three
explicit rules. Full contract: [FINANCE_MODEL.md](../design/FINANCE_MODEL.md).

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

