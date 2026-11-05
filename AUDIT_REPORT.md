# ENGINEERING AUDIT: KIRILL9123/myAgent

**Date**: 2026-07-30
**Scope**: Full repository (backend, frontend, tests, docs, dev-tools)
**Method**: Read-only static analysis — every source file, test, and document inspected

---

## 1. REPOSITORY STRUCTURE

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan, middleware, scheduler
│   │   ├── agent/
│   │   │   ├── orchestrator.py        # Core agent loop, tool dispatch, confirmations
│   │   │   ├── llm_client.py          # Single Ollama HTTP client (+shutdown)
│   │   │   ├── tool_models.py         # Pydantic models + TOOL_MODEL_REGISTRY
│   │   │   └── scheduled_tasks.py     # Morning summary (scheduler job)
│   │   ├── api/
│   │   │   ├── chat.py                # POST /api/chat, GET /api/history/{session_id}
│   │   │   ├── calendar.py            # CRUD routes for calendar events
│   │   │   ├── mail.py                # Routes: unread, search, send
│   │   │   ├── finance.py             # Routes: transactions, summary, recurring
│   │   │   ├── memory.py              # Routes: pending, approve, reject, graph, consolidate
│   │   │   └── utils.py               # run_api_tool() helper
│   │   ├── connectors/
│   │   │   ├── caldav_connector.py    # iCloud CalDAV: list, search, create, modify, delete
│   │   │   └── mail_connector.py      # IMAP/SMTP: list_unread, search, send (Gmail/UkrNet)
│   │   ├── core/
│   │   │   └── execution_mode.py      # DRY_RUN/REAL mode from env var
│   │   ├── audit/
│   │   │   └── audit_log.py           # Rotating file audit logger
│   │   ├── permissions/
│   │   │   ├── permission_checker.py  # JSON-based permission lookup
│   │   │   └── tool_permissions.json  # 16 action entries (2 unused)
│   │   ├── memory/
│   │   │   ├── memory_service.py      # Facts CRUD, relationships, consolidation, retrieval
│   │   │   ├── fact_extractor.py      # LLM-based fact extraction + dedup
│   │   │   └── relation_builder.py    # LLM-based relationship suggestions
│   │   ├── finance/
│   │   │   └── finance_service.py     # Transactions, recurring templates, summary
│   │   ├── countdown/
│   │   │   ├── countdown_service.py   # Add/get/delete countdowns
│   │   │   └── countdown_routes.py    # FastAPI router for countdowns
│   │   ├── notifications/
│   │   │   ├── telegram_notifier.py   # Send Telegram messages (dry-run guarded)
│   │   │   └── telegram_listener.py   # Long-polling Telegram bot
│   │   ├── storage/
│   │   │   ├── db.py                  # SQLite schema, migrations, CRUD helpers
│   │   │   └── backup.py              # Online backup, restore, retention
│   │   └── voice/
│   │       └── transcriber.py         # openai-whisper local STT
│   └── tests/
│       ├── test_tool_validation.py    # 30+ tests: Pydantic models + registry
│       ├── test_dry_run.py            # 12 tests: side-effect guards for all connectors
│       ├── test_memory_flow.py        # Manual integration test (async main())
│       ├── test_confirmation_logic.py # Manual test: RED confirmation matching
│       ├── test_api_endpoints.py      # Manual test: API routes with TestClient
│       ├── test_temporal_memory.py    # 8 pytest tests: temporal validity
│       ├── test_memory_filter.py      # Manual test: keyword filtering + LLM shortcut
│       └── test_backup.py             # 5 pytest tests: backup/restore/retention
├── frontend/
│   └── src/
│       ├── App.tsx                    # SPA router with 6 pages
│       ├── main.tsx                   # React entry point
│       ├── pages/                     # Dashboard, Chat, Memory, Calendar, Mail, Finance, Countdowns
│       ├── components/                # AppShell, MemoryGraph, PendingFactsQueue, ConsolidationQueue
│       └── api/                       # chat, calendar, mail, finance, memory, countdown clients
├── dev-tools/
│   ├── test_caldav.py                 # Direct CalDAV connector call
│   ├── test_mail.py                   # Direct IMAP connection
│   ├── test_gmail.py                  # Print credential env vars
│   ├── test_gmail2.py                 # Direct IMAP connection to Gmail
│   ├── test_morning_summary.py        # Run morning_summary() directly
│   ├── test_summary.py                # Duplicate of test_morning_summary
│   └── restore_backup.py              # Interactive restore CLI
├── docs/                              # 14 markdown files (planning/reference)
├── .env.example                       # 15 env vars documented
├── requirements.txt                   # 8 dependencies (ollama has no version pin)
└── README.md                          # Accurate setup instructions
```

---

## 2. CURRENT IMPLEMENTATION STATUS

| Feature / Subsystem | Status | Evidence | Problems |
|---|---|---|---|
| FastAPI app startup | IMPLEMENTED | `main.py` lines 1-148 | No EXECUTION_MODE guard on Telegram listener startup |
| API auth middleware | IMPLEMENTED | `main.py` lines 113-130 | API key check skips non-/api paths entirely |
| Orchestrator | IMPLEMENTED | `orchestrator.py` `run_orchestrator()` | Duplicate `_background_tasks`/`_log_task_exception` (also in main.py); `_dispatch_tool` has inline imports |
| LLM interaction | IMPLEMENTED | `llm_client.py` `chat_with_ollama()` | 8 call sites, hardcoded Ollama dependency, no retry/fallback |
| Tool calling | IMPLEMENTED | `orchestrator.py` `AVAILABLE_TOOLS` + `_dispatch_tool()` | Inline schema definitions duplicated from Pydantic models |
| Tool validation | IMPLEMENTED | `orchestrator.py` `execute_tool()` lines ~420-440 | Validation happens AFTER parsing, but BEFORE permission check — correct |
| Permission checks | IMPLEMENTED | `permission_checker.py` + `tool_permissions.json` | 2 entries unused (`create_reminder`, `bulk_delete`); `delete_countdown` is YELLOW but has no explicit confirmation requirement |
| RED confirmation | IMPLEMENTED | `orchestrator.py` `_check_confirmation()` | Robust: positional guards, existential negation bypass, short-message filter |
| Dry-run / execution mode | **PARTIAL** | `execution_mode.py` + guarded in 7 functions | `add_countdown` and `delete_countdown` have NO dry-run guard. `list_unread_emails` (read) mutates sync state with NO guard. API routes bypass dry-run: they call connectors directly without checking mode |
| Audit logging | IMPLEMENTED | `audit_log.py` + calls throughout orchestrator | Only orchestrator path logs; direct API calls and dev-tools do NOT log |
| Calendar | IMPLEMENTED | `caldav_connector.py` | In-memory cache unsynchronized across workers; API routes bypass orchestrator — no permission/confirmation/audit |
| Email | IMPLEMENTED | `mail_connector.py` | Same API bypass issue; `list_unread_emails` mutates DB sync state |
| Telegram | IMPLEMENTED | `telegram_listener.py` + `telegram_notifier.py` | Listener starts at app boot with no EXECUTION_MODE guard; approved chat_id only |
| Finance | IMPLEMENTED | `finance_service.py` + API routes | `add_transaction` dry-run guarded; API routes call service directly |
| Countdowns | IMPLEMENTED | `countdown_service.py` + routes | **No dry-run guard** on `add_countdown` or `delete_countdown` |
| Scheduler | IMPLEMENTED | `main.py` lifespan: 4 cron jobs | All start at boot; `morning_summary` calls `send_notification` (dry-run guarded) but `list_events` and `list_unread_emails` are NOT guarded |
| Memory | IMPLEMENTED | `memory_service.py`, `fact_extractor.py`, `relation_builder.py` | Full lifecycle; **no dry-run guard** on any memory write |
| Temporal memory | **IMPLEMENTED** | `db.py` migrations + `memory_service.py` `get_approved_facts()` filter | Working: `valid_from`, `valid_to`, `source_type`, `last_confirmed_at` columns exist and are used |
| Memory provenance/confidence | **PARTIAL** | `source_type` column exists; `confidence` field exists | `source_type` set to `"llm_extraction"` or `"manual_consolidation"` but `source_conversation_id` often NULL; no source reference trail |
| Backup | IMPLEMENTED | `backup.py` `create_backup()` | Uses SQLite online backup API; integrity checks; metadata JSON |
| Restore | IMPLEMENTED | `backup.py` `restore_backup()` + CLI | Creates pre-restore snapshot; uses atomic os.replace(); interactive CLI |
| Frontend dashboard | IMPLEMENTED | `DashboardPage.tsx` | Working 4-widget layout; graceful error states |
| Frontend API comm | IMPLEMENTED | `api/*.ts` | API key from env var; proper headers |
| Error handling | IMPLEMENTED | `run_api_tool()` + FastAPI exception handlers | OK for API routes; orchestrator errors returned inline |
| Configuration | IMPLEMENTED | `.env` via `python-dotenv` | 15 env vars documented |
| Secrets handling | IMPLEMENTED | Env vars only | No secret manager; `.env` is `.gitignore`d but `.env.example` confirms architecture |
| CI/CD | **NOT IMPLEMENTED** | No `.github/`, no Makefile, no CI config | Tests exist but must be run manually |
| pytest configuration | **NOT IMPLEMENTED** | No `pytest.ini`, `pyproject.toml`, or `conftest.py` | Some tests use pytest, some use `if __name__ == "__main__"` |
| Type hints | **PARTIAL** | Present in `orchestrator.py`, `tool_models.py`; missing/incomplete in `caldav_connector.py`, `mail_connector.py`, `db.py`, `main.py` | Inconsistent return type annotations |
| Token counting | **NOT IMPLEMENTED** | No code found | Risk of silent context window overflow |

---

## 3. CRITICAL END-TO-END FLOWS

### A. User Chat Flow

**Actual path:**
1. `POST /api/chat` → `chat_endpoint()` in `api/chat.py`
2. `run_orchestrator(user_message, session_id)` called
3. `_check_confirmation()` - checks for pending RED action
4. `save_message()` - saves user message to SQLite
5. `get_relevant_facts()` - keyword filter → possibly LLM filter
6. `get_history()` - retrieves last 20 messages
7. System prompt constructed with facts injected
8. `chat_with_ollama(messages, tools=AVAILABLE_TOOLS)` - single Ollama call
9. Multi-turn loop: for each tool call, `execute_tool()` → Pydantic validation → permission check → dispatch
10. For RED tools: `save_pending_action()`, return confirmation message
11. For GREEN/YELLOW: execute, sanitize result, continue loop
12. On text response: save assistant message, background `extract_facts_from_conversation()`
13. Return `ChatResponse`

**Verified:** Fully functional. Background fact extraction uses `asyncio.create_task()` with proper task tracking.

**Gap:** No token counting before LLM call.

### B. RED Action Flow

**Actual path:**
1. LLM requests RED tool (e.g., `send_email`)
2. `execute_tool()` → `check_permission()` returns `PermissionLevel.RED`
3. `save_pending_action(session_id, function_name, arguments)`
4. Returns `{"requires_confirmation": True, "message": "..."}`
5. Frontend shows yellow confirmation panel
6. User clicks "Да" → frontend sends "да" as chat message
7. `_check_confirmation()` matches "да" → `delete_pending_action()` → `_dispatch_tool()` → real execution
8. Result saved to history, audit logged

**Verified:** Fully functional. Second RED action in same round is blocked with error, preventing double-pending.

**Safety verified:** Red action NEVER executes without explicit matching confirmation in the very next message.

### C. Dry-run Flow

**Actual path (for guarded tools):**
1. Tool called (e.g., `send_email`)
2. `is_dry_run()` → True (default)
3. Returns `{"status": "dry_run", "would_do": {...}}`
4. No real side effect

**CRITICAL GAPS found:**

1. **API routes bypass dry-run**: `api/calendar.py`, `api/mail.py`, `api/finance.py` call connectors directly via `run_api_tool()`. These routes do NOT check `is_dry_run()`. The dry-run guard is only inside the connector functions themselves. For most write connectors (create_event, delete_event, modify_event, send_email, add_transaction, delete_transaction) this works because each function has its own guard. BUT:

2. **`add_countdown()` has NO dry-run guard** — writes to DB unconditionally.

3. **`delete_countdown()` has NO dry-run guard** — writes to DB unconditionally.

4. **`list_unread_emails()` mutates sync state** — writes `last_seen_uid` to DB without dry-run check.

5. **All memory operations have NO dry-run guard** — `save_pending_fact`, `approve_fact`, `reject_fact`, `consolidate_facts`, `save_relation`, `mark_facts_as_merged` all write to DB unconditionally.

### D. Memory Flow

**Actual path:**
1. Chat response completes → background `extract_facts_from_conversation()`
2. LLM call: extract facts as JSON array
3. For each fact: LLM call for deduplication against existing facts
4. If duplicate → `update_fact_timestamp()`
5. If new → `save_pending_fact()` with `status='pending_approval'`
6. Frontend Memory tab → Pending Facts Queue
7. User approves → `approve_fact()` → `status='approved'` + `last_confirmed_at`
8. On approve: `suggest_relations()` LLM call → save relations
9. Nightly: `run_scheduled_consolidation()` → precompute consolidation suggestions
10. User can trigger consolidation → `consolidate_facts()` merges into new fact

**Verified:** Full lifecycle working.

**Problems:**
- N+1 LLM calls: one extraction call + N dedup calls (one per fact) + relation suggestion call. This is 1 + N + 1 = potentially 5+ LLM calls per chat turn.
- `source_conversation_id` passed to `extract_facts_from_conversation()` but the orchestrator passes `None` (the background task doesn't capture the conversation ID).
- No dry-run guard on any memory operation.

### E. Scheduled Task Flow

**Actual path (morning summary):**
1. APScheduler fires `morning_summary` at configured time
2. `list_events()` for today — **no dry-run guard on the read itself, but could try to connect to real CalDAV**
3. `list_unread_emails()` — **no dry-run guard, mutates sync state**
4. `chat_with_ollama()` to generate summary
5. `send_notification()` — **dry-run guarded**
6. Logs to `summaries.log`

**Problems:**
- Scheduler starts at boot with no EXECUTION_MODE check
- `morning_summary` connects to CalDAV and IMAP unconditionally
- No error recovery if connectors fail

---

## 4. SAFETY AND SIDE-EFFECT AUDIT

### Every dangerous path and its guards:

| Path | Can send email? | Guard | Can modify calendar? | Guard | Can send Telegram? | Guard | Can modify DB? | Guard |
|---|---|---|---|---|---|---|---|---|
| `send_email()` (connector) | YES | `is_dry_run()` | - | - | - | - | - | - |
| `create_event()` (connector) | - | - | YES | `is_dry_run()` | - | - | - | - |
| `delete_event()` (connector) | - | - | YES | `is_dry_run()` | - | - | - | - |
| `modify_event()` (connector) | - | - | YES | `is_dry_run()` | - | - | - | - |
| `add_transaction()` (service) | - | - | - | - | - | - | YES | `is_dry_run()` |
| `delete_transaction()` (service) | - | - | - | - | - | - | YES | `is_dry_run()` |
| `add_countdown()` (service) | - | - | - | - | - | - | YES | **NONE** |
| `delete_countdown()` (service) | - | - | - | - | - | - | YES | **NONE** |
| `list_unread_emails()` (connector) | - | - | - | - | - | - | YES (sync_state) | **NONE** |
| Memory operations | - | - | - | - | - | - | YES | **NONE** |
| `send_notification()` (notifier) | - | - | - | - | YES | `is_dry_run()` | - | - |
| Telegram listener | - | - | - | - | YES (responds) | **NONE** | - | - |
| Morning summary | Indirect | Partial | Indirect | Partial | YES | Partial | YES (sync_state) | Partial |
| Dev-tools scripts | YES | **NONE** | YES | **NONE** | - | - | YES | **NONE** |

### Findings ranked by severity:

**CRITICAL:**
1. **`add_countdown()` and `delete_countdown()` have NO dry-run guard** (`backend/app/countdown/countdown_service.py` lines 9, 53). These directly write to SQLite. In dry-run mode, the orchestrator will pass through `_dispatch_tool()` → `add_countdown()`/`delete_countdown()` which writes to the real DB.

2. **`list_unread_emails()` mutates DB sync state with NO dry-run guard** (`backend/app/connectors/mail_connector.py` lines 117-123). Calling this in dry-run permanently updates `last_seen_uid`, making emails invisible on next real run.

3. **Memory operations have NO dry-run guard** — `save_pending_fact`, `approve_fact`, `reject_fact`, `consolidate_facts` all write to DB unconditionally. The orchestrator's fact extraction fires as a background task and writes facts with no mode check.

**HIGH:**
4. **API routes bypass orchestrator permission/confirmation/audit** — `POST /api/calendar/events` calls `create_event()` directly, skipping permission check, RED confirmation, and audit logging. An authenticated API call can create/delete/modify calendar events, send emails, and add transactions without any safety barrier.

5. **Telegram listener starts at boot with NO EXECUTION_MODE guard** (`main.py` line 80). In dry-run, the bot still polls and can receive/respond to real messages. While `send_notification` is guarded, the listener connects to the real Telegram API and processes real user inputs.

6. **Dev-tools scripts can trigger real side effects** — `test_morning_summary.py` calls `morning_summary()` directly; `test_caldav.py` calls `list_events()`; `test_gmail2.py` connects IMAP; `test_mail.py` connects IMAP. All bypass dry-run since they import and call functions directly.

**MEDIUM:**
7. **Morning summary connects to CalDAV/IMAP unconditionally** — in dry-run mode, `list_events()` runs against real CalDAV and `list_unread_emails()` mutates sync state.

8. **Only one pending RED action per session** — if the LLM proposes two RED actions in one round, the second is silently dropped with an error message to the LLM. The user never sees it.

9. **No audit logging for API routes** — the audit log only records actions flowing through the orchestrator. Direct API calls go unlogged.

**LOW:**
10. **Cached connector responses** — CalDAV and mail connectors use in-memory caches. In a multi-worker setup, this would cause stale data. Currently single-process, so low priority.

---

## 5. TOOL SYSTEM AUDIT

### Tool inventory:

| Tool | Pydantic Model | Permission | Confirmation | Dry-run | Audit | Tests |
|---|---|---|---|---|---|---|
| `list_events` | `ListEventsArgs` | GREEN | No | N/A (read) | Via orchestrator | Valid+invalid |
| `search_events` | `SearchEventsArgs` | GREEN | No | N/A (read) | Via orchestrator | Valid+invalid |
| `list_unread_emails` | `ListUnreadEmailsArgs` | GREEN | No | **NO (mutates DB)** | Via orchestrator | Valid+invalid |
| `search_emails` | `SearchEmailsArgs` | GREEN | No | N/A (read) | Via orchestrator | Valid+invalid |
| `send_email` | `SendEmailArgs` | RED | Yes | YES | Yes | Valid+invalid+dry-run |
| `create_event` | `CreateEventArgs` | YELLOW | No | YES | Via orchestrator | Valid+invalid+dry-run |
| `delete_event` | `DeleteEventArgs` | RED | Yes | YES | Via orchestrator | Valid+invalid+dry-run |
| `modify_event` | `ModifyEventArgs` | RED | Yes | YES | Via orchestrator | Valid+invalid+dry-run |
| `add_transaction` | `AddTransactionArgs` | GREEN | No | YES | Via orchestrator | Valid+invalid+dry-run |
| `get_transactions` | `GetTransactionsArgs` | GREEN | No | N/A (read) | Via orchestrator | Valid |
| `get_summary` | `GetSummaryArgs` | GREEN | No | N/A (read) | Via orchestrator | Valid |
| `add_countdown` | `AddCountdownArgs` | GREEN | No | **NO** | Via orchestrator | Valid+invalid |
| `get_all_countdowns` | `GetAllCountdownsArgs` | GREEN | No | N/A (read) | Via orchestrator | Valid |
| `delete_countdown` | `DeleteCountdownArgs` | YELLOW | **No (should be RED?)** | **NO** | Via orchestrator | Valid+invalid |

### Duplication assessment:

Tool definitions exist in **3 separate places:**
1. `AVAILABLE_TOOLS` list in `orchestrator.py` (LLM-facing JSON schemas)
2. `_dispatch_tool()` in `orchestrator.py` (dispatch if/elif chain)
3. `TOOL_MODEL_REGISTRY` in `tool_models.py` (Pydantic models)
4. `tool_permissions.json` (permission levels)

These 4 are NOT derived from a single source of truth. Adding a new tool requires editing all 4 locations.

**Registry readiness:** The code has enough duplication that a centralized Tool Registry would immediately eliminate 3 of 4 definition locations. The Pydantic models and `TOOL_MODEL_REGISTRY` already provide the foundation.

---

## 6. MODEL / LLM ARCHITECTURE AUDIT

### Every `chat_with_ollama` call site:

| # | File | Function | Purpose | Model | JSON Mode? | Tools? | Retry? |
|---|---|---|---|---|---|---|---|
| 1 | `orchestrator.py:683` | `run_orchestrator()` | Main chat + tool calling | `OLLAMA_MODEL` | No | Yes | No |
| 2 | `scheduled_tasks.py:68` | `morning_summary()` | Morning summary generation | `OLLAMA_MODEL` | No | No | No |
| 3 | `memory_service.py:364` | `get_relevant_facts()` | LLM fact relevance filter | `OLLAMA_MODEL` | Yes | No | No |
| 4 | `memory_service.py:427` | `find_consolidation_candidates()` | Consolidation suggestions | `OLLAMA_MODEL` | Yes | No | No |
| 5 | `fact_extractor.py:67` | `extract_facts_from_conversation()` | Fact extraction | `OLLAMA_MODEL` | Yes | No | No |
| 6 | `fact_extractor.py:131` | `extract_facts_from_conversation()` | Dedup check (per fact) | `OLLAMA_MODEL` | Yes | No | No |
| 7 | `relation_builder.py:48` | `suggest_relations()` | Relation building | `OLLAMA_MODEL` | Yes | No | No |

**8 direct `chat_with_ollama` call sites across 5 files.** All hardcode `OLLAMA_MODEL` from env var.

### Assessment:
- **Difficulty to replace Ollama**: MEDIUM. The `chat_with_ollama` function is a simple HTTP wrapper. Replacing it requires changing exactly one function. But the call sites are spread across 5 modules.
- **Model-specific logic leaking**: LOW. The only model-specific assumption is that the API supports `tools` array and `response_format="json"` — both are standard OpenAI-compatible features.
- **Different tasks need different models**: YES. Fact extraction needs JSON reliability; tool calling needs function-calling support; morning summary just needs good Russian text generation. Currently all use the same model.
- **ModelProvider abstraction justified NOW**: YES, but a minimal one. All 8 calls pass the same message format. A small `ModelProvider` interface with `chat(messages, **kwargs)` → `dict` would be sufficient.
- **Smallest safe abstraction**: A single `ModelProvider` class with a `chat()` method, an `OllamaProvider`, and a factory function reading from env vars. Do NOT over-design with model roles or registries before the basic abstraction exists.

---

## 7. MEMORY AUDIT

### Database schema:
- `user_facts`: id, content, category, source_conversation_id, confidence, created_at, updated_at, status, merged_into_id, last_confirmed_at, valid_from, valid_to, source_type
- `fact_relations`: id, fact_a_id, fact_b_id, relation_type, created_at

### Lifecycle verified:
1. Background extraction after each chat turn → `extract_facts_from_conversation()`
2. LLM extraction + per-fact LLM dedup → `save_pending_fact()` with `status='pending_approval'`
3. User approves → `approve_fact()` → `status='approved'` + `last_confirmed_at=CURRENT_TIMESTAMP`
4. On approve → `suggest_relations()` LLM call → `save_relation()`
5. Retrieval: `get_relevant_facts()` → keyword filter → optional LLM relevance filter
6. Consolidation: nightly job → `find_consolidation_candidates()` → UI → `consolidate_facts()`

### Temporal memory assessment:
- **`valid_from`**: Set to `CURRENT_TIMESTAMP` on insert via `save_pending_fact()`. Migrated column exists.
- **`valid_to`**: Null by default (no expiry). Can be set via `PATCH /api/memory/facts/{id}/validity`. Filtered in `get_approved_facts()` with `WHERE valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP`.
- **`last_confirmed_at`**: Set on approval. Migrated column exists.
- **`source_type`**: Set to `"llm_extraction"` or `"manual_consolidation"`. Default "unknown" for legacy rows.
- **Expired facts**: Correctly excluded from retrieval and approved facts list. Verified by `test_temporal_memory.py`.

### Problems found:
1. **N+1 LLM calls**: One extraction + N dedup calls + 1 relation call = up to 5+ LLM calls per chat turn
2. **`source_conversation_id` is NULL**: In `orchestrator.py` line ~700, the background task calls `extract_facts_from_conversation(conversation_snippet)` without passing `source_conversation_id`. The parameter defaults to `None`.
3. **No dry-run guard on any memory write**
4. **`_RUSSIAN_STOPWORDS` uses hardcoded set** — effective but not configurable
5. **`EMBEDDING_THRESHOLD = 100`** — hardcoded warning, no actual embedding implementation yet (correctly deferred per roadmap)
6. **Consolidation `save_approved_fact` hardcodes `confidence=0.95`** — arbitrary, should be configurable

---

## 8. BACKUP / RESTORE AUDIT

### Implementation verified:
- **Backup creation**: Uses SQLite `connection.backup()` API (online, safe, non-blocking). `create_backup()` in `backup.py`.
- **Integrity check**: `PRAGMA integrity_check` on backup after creation. Returns "ok" or specific error.
- **Metadata**: JSON sidecar with timestamp, source path, integrity result, table counts.
- **Retention**: Keep 14 most recent, delete older. `apply_retention_policy()` called after each backup.
- **Scheduler**: Daily backup at 02:00 via APScheduler.
- **Restore**: Creates pre-restore snapshot, then `os.replace()` (atomic) to swap in backup. Integrity check after restore.
- **CLI**: Interactive `dev-tools/restore_backup.py` with confirmation ("Type YES").
- **Tests**: `test_backup.py` — 5 pytest tests covering creation, retention (14 kept), restore from clean, restore not found, empty dir.

### Assessment: **Production-usable.** The implementation is solid and well-tested. The pre-restore snapshot is smart.

### Minor issues:
- No WAL mode configuration
- No encryption at rest (delegated to filesystem per plan)
- Retention is flat (no weekly/monthly tiers as described in plan)

---

## 9. TESTING AND CI AUDIT

### Current test landscape:

| File | Framework | Type | Count | What it tests |
|---|---|---|---|---|
| `test_tool_validation.py` | pytest | Unit | 30+ | Pydantic models, registry completeness, validation-before-permission |
| `test_dry_run.py` | pytest | Integration | 12 | Side-effect guards for all connectors |
| `test_temporal_memory.py` | pytest | Integration | 8 | Temporal validity fields, filtering, PATCH endpoint |
| `test_backup.py` | pytest | Unit | 5 | Backup creation, retention, restore, not-found |
| `test_memory_filter.py` | manual (`asyncio.run`) | Integration | 5 | Keyword filter, LLM shortcut, stopwords |
| `test_memory_flow.py` | manual (`asyncio.run`) | Integration | ~5 | Fact extraction, dedup, approval, graph |
| `test_confirmation_logic.py` | manual (`asyncio.run`) | Unit | 6 | RED confirmation matching, negation bypass |
| `test_api_endpoints.py` | manual | Integration | 6 | API routes with TestClient |

### Assessment:
- **Total: ~77 tests across 8 files**
- **Framework split**: 4 pytest files (55+ tests), 4 manual `asyncio.run()` files (22+ tests)
- **Manual tests use real SQLite** — `test_home_agent.db` created and deleted per run
- **Pytest tests use proper isolation** — `tmp_path` fixture for backup, `monkeypatch` for env vars
- **No CI**: No `.github/`, no CI config
- **No pytest config**: No `pytest.ini`, `pyproject.toml`, or `conftest.py`
- **Test discovery is broken by design**: The 4 manual tests have `if __name__ == "__main__"` blocks and cannot be discovered by pytest

### Important untested paths:
- Orchestrator end-to-end with real LLM simulation
- Permission enforcement (no test directly verifies RED tools require confirmation)
- API auth middleware
- Telegram listener message processing
- Scheduler job execution
- Error recovery paths
- Concurrent session handling

### Do tests protect against dangerous regressions?
**Partially.** `test_dry_run.py` is excellent — it verifies that all 7 side-effecting functions return `would_do` payloads and don't call real services. But the gap is that `add_countdown` and `delete_countdown` are NOT tested for dry-run (because they don't HAVE the guard). The tests catch what they test, but the untested paths are the dangerous ones.

---

## 10. TYPE SAFETY AND CODE QUALITY

### Concrete issues found:

1. **Duplicate code**: `_background_tasks` and `_log_task_exception` defined identically in BOTH `main.py` (lines 87-100) and `orchestrator.py` (lines 713-722).
2. **`_background_tasks` redefined** in `orchestrator.py` shadows the module-level name from `main.py`.
3. **`load_dotenv()` called in connector files** — `caldav_connector.py` line 4 and `mail_connector.py` line 11. Unnecessary since `python-dotenv` should be called once at app startup.
4. **Inline imports in `_dispatch_tool()`** — 7 inline imports for services/connectors. Makes static analysis harder.
5. **`list_events()` return type inconsistency**: Returns `list[dict]` on success, `dict` (error object) on failure. Type hint says `list[dict[str, Any]]` but actually returns `dict` on error.
6. **Missing type annotations**: `caldav_connector.py` uses `Any` extensively; `db.py` functions have no return type annotations; `main.py` has no type annotations on most functions.
7. **Broad exception handling**: `except Exception as e` used extensively in `_dispatch_tool`, connectors, memory service. Swallows specific errors.
8. **Global mutable state**: `_cached_calendars`, `_cached_primary_calendar`, `_events_cache` in caldav_connector; `_unread_cache` in mail_connector; `_consolidation_cache` in memory_service. All module-level mutable globals.
9. **`ollama` in requirements.txt has no version pin** — vulnerable to breaking changes.
10. **`requirements.txt` is minimal** — 8 dependencies. Missing `pytest` (if you want to run tests). Missing any dev dependency group.

---

## 11. DOCUMENTATION ACCURACY

### Document-by-document comparison:

| Document | Accuracy | Issues |
|---|---|---|
| **README.md** | ✅ ACCURATE | Setup instructions match reality. Model name is `qwen2.5:7b` in README but `qwen3:30b-a3b` in `.env.example` — minor discrepancy. |
| **ARCHITECTURE.md** | ✅ MOSTLY ACCURATE | Correctly describes data flow. References "Mem0 removed" — accurate. Architecture diagram matches code. |
| **ARCHITECTURE_STATUS.md** | ✅ MOSTLY ACCURATE | All "Implemented" items verified. "Fixed" annotations correct. Would benefit from noting the countdown dry-run gap. |
| **ROADMAP.md** | ⚠️ STALE | Phase 1 checklist: "pytest + CI" and "type hints" and "token counting" and "N+1 LLM calls" marked incomplete — accurate. "Fix known contract inconsistencies" marked complete — all 4 items verified fixed. "Fact confidence / temporal validity" marked complete — **verified implemented**. All Phase 2-6 items correctly marked as planned. |
| **BACKLOG.md** | ⚠️ STALE | Says "Cycle complete — awaiting next selection." Reflects that no active cycle is in progress. Parking lot items are accurate. |
| **ENGINEERING_RULES.md** | ✅ ACCURATE | 5 rules all correspond to actual code invariants. |
| **DRY_RUN_ARCHITECTURE.md** | ⚠️ STALE | Claims all side-effecting tools are guarded. **`add_countdown` and `delete_countdown` are NOT.** Proposed "Fake connectors" not implemented. "Tests must fail if production credentials are present" — not implemented. |
| **TOOL_VALIDATION_PLAN.md** | ✅ ACCURATE | Migration plan fully executed. Pydantic models exist and are integrated. Full registry refactor correctly deferred. |
| **BACKUP_RESTORE_PLAN.md** | ⚠️ PARTIALLY STALE | Implementation simplified from plan: flat 14-day retention instead of daily/weekly/monthly tiers. No encryption. But core functionality matches plan. |
| **MEMORY_EVOLUTION.md** | ✅ ACCURATE | "Missing fields" list: provenance, `last_confirmed_at`, temporal validity — all three are now IMPLEMENTED. Decay scoring correctly still listed as planned. |
| **DEVELOPMENT_DEPENDENCIES.md** | ✅ ACCURATE | Core chain correctly describes dependencies. Safety dependencies still accurate. |

### Key discrepancies:
1. **DRY_RUN_ARCHITECTURE.md says "all networked connectors require policy"** but countdowns don't check it.
2. **ROADMAP.md marks Phase 1 dry-run/side-effect isolation as complete** but countdown and memory operations are unguarded.
3. **README model name**: `qwen2.5:7b` vs `.env.example`: `qwen3:30b-a3b`.

---

## 12. NEXT DEVELOPMENT CYCLE READINESS

| Direction | Readiness | Value | Risk | Dependencies | Blocking Issues |
|---|---|---|---|---|---|
| **A. Finish Phase 1 quality/safety** | 85% | HIGH | LOW | None | Missing dry-run guards on countdown + memory; no CI; no pytest config |
| **B. Model Abstraction Layer** | 60% | HIGH | LOW | None; but safety gaps should be fixed first | 8 call sites to refactor; no test infrastructure for provider mocking |
| **C. Centralized Tool Registry** | 70% | MEDIUM | LOW | Pydantic models exist; needs B for clean design | Tool definitions in 4 places; API bypass needs addressing first |
| **D. Commitment Tracker** | 10% | MEDIUM | MEDIUM | Schema design not started; needs dry-run + backup solid | No implementation; purely a domain contract document |
| **E. Personal State / RAG** | 5% | LOW | HIGH | Needs C, D, and embedding infrastructure | Explicitly conditional on Phase 4; massive scope; no justification yet |

### Recommended NEXT cycle (max 4 tasks):

1. **Close remaining dry-run gaps** — Add `is_dry_run()` guards to `add_countdown()`, `delete_countdown()`, and `list_unread_emails()` sync-state mutation. Add tests.
2. **Set up pytest + CI** — Create `pytest.ini`, convert 4 manual tests to pytest, add `.github/workflows/test.yml`.
3. **Model Abstraction Layer (minimal)** — `ModelProvider` ABC with single `chat()` method, `OllamaProvider`, config-driven selection. Replace all 8 `chat_with_ollama` calls.
4. **Add token counting** — Simple tiktoken-based counting before LLM calls, with configurable warning/cutoff thresholds.

---

## 13. TOP RISKS

| # | Severity | Location | Description | Failure Scenario | Fix Direction |
|---|---|---|---|---|---|
| 1 | **CRITICAL** | `countdown_service.py:9,53` | `add_countdown()` and `delete_countdown()` have no dry-run guard | User runs in dry-run mode, LLM adds/deletes countdowns, real DB modified | Add `is_dry_run()` check at top of both functions |
| 2 | **CRITICAL** | `mail_connector.py:117-123` | `list_unread_emails()` permanently mutates sync state regardless of mode | Dry-run mode burns through unseen emails; on next real run, no emails appear | Add `is_dry_run()` guard before `update_last_seen_uid()` |
| 3 | **HIGH** | `api/calendar.py`, `api/mail.py`, `api/finance.py` | API routes bypass orchestrator → no permission check, no RED confirmation, no audit | Attacker with API key sends `POST /api/mail/send` → email sent with no confirmation | Route API write calls through orchestrator or add middleware guards |
| 4 | **HIGH** | `main.py:80` | Telegram listener starts regardless of `EXECUTION_MODE` | Dry-run mode: bot still responds to real Telegram messages | Guard `start_polling()` with `is_dry_run()` check |
| 5 | **HIGH** | `dev-tools/test_morning_summary.py`, `test_caldav.py`, `test_gmail2.py` | Dev scripts call real services with no safety guard | Developer runs `python dev-tools/test_morning_summary.py` → real Telegram message sent, real DB mutated | Add `EXECUTION_MODE` check at top of each script |
| 6 | **HIGH** | All memory write operations | `save_pending_fact`, `approve_fact`, `reject_fact`, `consolidate_facts` have no dry-run guard | Background fact extraction writes facts in dry-run mode | Add mode check in memory_service write operations |
| 7 | **MEDIUM** | `orchestrator.py:700` | `extract_facts_from_conversation()` called with `source_conversation_id=None` | Fact provenance trail broken; can't trace facts back to source conversation | Pass the conversation ID from the saved message |
| 8 | **MEDIUM** | `llm_client.py` | No retry or fallback on Ollama failure | Ollama crashes → all agent functionality fails with opaque error | Add retry with exponential backoff; graceful error response |
| 9 | **MEDIUM** | `tool_permissions.json` | `delete_countdown` is YELLOW (no confirmation) while `delete_event` is RED (requires confirmation) | Inconsistency: deleting a countdown doesn't ask for confirmation | Either make `delete_countdown` RED or document why it's YELLOW |
| 10 | **MEDIUM** | No CI | Tests exist but are never run automatically | Regression introduced, nobody notices until manual test run | Add GitHub Actions workflow running pytest |

---

## 14. FINAL EXECUTIVE SUMMARY

## CURRENT STATE

- Fully functional FastAPI backend with orchestrator loop, tool calling, permission gating, and RED confirmation for high-impact actions
- 14 LLM-accessible tools across Calendar, Email, Finance, and Countdown domains
- Custom SQLite-backed Memory Layer with fact extraction, deduplication, human approval, relation graph, and consolidation
- Dry-run/side-effect isolation for 7 of 9 write paths (critical gaps in countdown and memory)
- SQLite online backup with integrity checks, metadata, retention, atomic restore, and interactive CLI
- Temporal memory metadata (valid_from, valid_to, source_type, last_confirmed_at) with expired-fact filtering
- React + TypeScript + Vite frontend with 6 pages: Dashboard, Chat, Memory Graph, Calendar, Mail, Finance, Countdowns
- Telegram bot with long-polling listener and voice message transcription via Whisper
- Morning summary scheduler with LLM-generated briefings sent via Telegram
- 77 tests across 8 files covering tool validation, dry-run, temporal memory, backup, memory filtering, and confirmation logic

## WHAT IS WORKING WELL

- **Permission architecture**: GREEN/YELLOW/RED classification with JSON config, enforced in deterministic Python code, not in prompts. RED confirmation flow is robust with positional guards and existential negation bypass.
- **Dry-run foundation**: The `execution_mode.py` module and connector-level guards are well-designed. `test_dry_run.py` provides strong regression protection for guarded paths.
- **Tool validation**: Pydantic models with `TOOL_MODEL_REGISTRY` provide type-safe argument validation before any permission check or execution.
- **Backup/restore**: Production-quality implementation with online backup API, integrity checks, atomic restore, pre-restore snapshots, and interactive CLI.
- **Memory lifecycle**: Complete flow from LLM extraction → dedup → pending → human approval → relation building → consolidation. Temporal filtering correctly excludes expired facts.
- **Frontend dashboard**: Clean, responsive design with proper loading/error states for all widgets.

## CRITICAL PROBLEMS

1. **Dry-run gaps in countdown and memory**: 2 countdown functions and all memory write operations bypass execution mode checks.
2. **API routes bypass safety**: Direct connector calls from `/api/calendar`, `/api/mail`, `/api/finance` skip the orchestrator's permission, confirmation, and audit layers.
3. **No CI**: 77 tests exist but are never automatically run. 4 test files use manual `asyncio.run()` pattern and can't be discovered by pytest.
4. **`list_unread_emails` mutates state in dry-run**: Sync state updates are not guarded.

## DOCUMENTATION VS REALITY

- `DRY_RUN_ARCHITECTURE.md` claims all side-effecting tools are guarded — **false**. Countdown and memory are not.
- `ROADMAP.md` Phase 1 dry-run/side-effect isolation marked complete — **partially true**. Foundation exists but countdown and memory gaps remain.
- `ARCHITECTURE_STATUS.md` "Implemented" list is accurate but omits the countdown dry-run gap.
- README model name (`qwen2.5:7b`) differs from `.env.example` (`qwen3:30b-a3b`).

## NEXT CYCLE RECOMMENDATION

1. **Close dry-run gaps** — Guards for `add_countdown`, `delete_countdown`, `list_unread_emails` sync state, and all memory writes. Tests for each.
2. **Set up pytest + CI** — `pytest.ini`, convert manual tests, `.github/workflows/test.yml`.
3. **Minimal ModelProvider abstraction** — Replace 8 `chat_with_ollama` calls with a single-provider interface. No over-design.
4. **Add token counting** — Prevent silent context window overflow.

## DO NOT BUILD YET

- **Commitment Tracker**: No schema, no implementation. Needs dry-run solid and CI first.
- **Personal State / RAG**: Explicitly conditional on Phase 4 completion. Massive scope. No justification from current usage.
- **Multi-agent architecture**: Roadmap correctly defers this. Single orchestrator is sufficient and well-implemented.
- **Centralized Tool Registry**: Would be nice but the current duplication is manageable for 14 tools. Fix safety gaps first.
- **Any new domain services**: Foundation quality issues (CI, dry-run gaps, type hints) must be resolved before expanding.

## CONFIDENCE

**Audit confidence: 85%**

Every Python source file, every test file, every documentation file, and every configuration file was read and traced. The following could not be verified:

- **Runtime behavior with actual Ollama**: No running Ollama instance available. All LLM call sites traced, but response parsing in production not verified.
- **CalDAV and IMAP connectivity**: Credential-dependent. Connector code paths verified; actual iCloud/Gmail behavior not tested.
- **Frontend build output**: `dist/` exists but was not diffed against source.
- **Telegram bot behavior**: Listener code verified; actual Telegram API behavior not tested.
- **Production deployment**: Single-machine Mac setup per README; multi-worker or containerized deployment not assessed.
