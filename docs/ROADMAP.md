# Roadmap

## Phase 1: Foundation (Completed)
- [x] Project scaffolding and documentation
- [x] FastAPI entrypoint
- [x] Whitelist permission system (green/yellow/red)
- [x] Tool calling loop with Ollama (local LLM)
- [x] iCloud CalDAV connector (Read-only: list/search events)

## Phase 2: Calendar Management & Email Reader
**Status: COMPLETED**
- [x] Create CalDAV connector with write capabilities
- [x] Implement multi-turn confirmation loop for safety
- [x] Create Email connector (IMAP) for reading emails
- [x] Update tool_permissions.json with new actions
- [x] Update frontend UI for basic chat capabilities

### Phase 3: Proactive Background Tasks 
**Status: COMPLETED**
- **Scheduler**: Added `apscheduler` and running as a background task.
- **Morning Summary Task**: Agent checks email/calendar every morning and generates an LLM summary.
- **Email Sending**: Agent can send emails via SMTP (requires explicit RED permission confirmation).
- **Notifications**: Summary is sent directly to the user via Telegram Bot API.

## Phase 4: Finance Module (MVP)
**Status: COMPLETED**
- [x] Create database tables for transactions and categories
- [x] Implement backend finance service and API endpoints
- [x] Register finance tools for the agent (green permission)
- [x] Refactor frontend into a multi-module dashboard (Chat, Finance)

## Phase 4.5: Countdowns / Deadlines
**Status: COMPLETED**
- [x] Create database table `countdowns`
- [x] Implement `countdown_service.py`
- [x] Add tools `add_countdown`, `get_all_countdowns`, `delete_countdown`
- [x] Add frontend Deadlines tab
- [x] Include countdowns in morning summary

## Phase 5: Voice Telegram Integration
**Status: COMPLETED**
- [x] Add `openai-whisper` for local voice recognition
- [x] Implement audio transcription in `backend/app/voice/transcriber.py`
- [x] Update Telegram listener to download and transcribe voice messages

## Phase 6: Smart Home Integration
**Status: POSTPONED (отложена по решению пользователя, не приоритет)**
- [ ] Connect to Home Assistant (REST/WebSocket API)
- [ ] Read-only state access for sensors and lights

## Phase 7: Complete Home Automation
- [ ] Allow the agent to control Home Assistant devices (turn on lights, adjust thermostat)
- [ ] Refine remote access via Tailscale and secure the web interface

## Phase 8: Memory Layer (Stable ✅ — future optimizations documented in NOTES.md)
- [x] Create SQLite DB schema for user facts and relations
- [x] Implement LLM fact extractor with semantic deduplication check
- [x] Implement LLM relation builder with closed type list
- [x] Create confirmation flow REST endpoints (get pending, approve, reject, get graph data)
- [x] Scaffold React + Vite + TS + Tailwind CSS frontend
- [x] Build Obsidian-style interactive force-directed memory graph view (visual styling, search query highlights, camera zoom controls, and slide-out details panel)
- [x] Add Approve/Reject pending facts review queue UI
- [x] Add backend relations backfill endpoint and trigger button in UI
- [x] Implement semantic fact consolidation flow (clustering candidates, POST-merge status update, and UI tab)

## Phase 8.1: Memory Integration in Orchestrator (Stable ✅)
- [x] Implement LLM-based `get_relevant_facts()` retrieval in `memory_service.py`
- [x] Inject relevant approved facts into orchestrator system prompt
- [x] Add background `extract_facts_from_conversation()` call after each LLM response
- [x] Replace Mem0/Qdrant integration with custom Memory Layer (human-in-the-loop)
- [x] Add debug logging for retrieved facts (`[MEMORY]` prefix in server logs)
- [x] Automated nightly consolidation via APScheduler (03:00, results cached for instant tab load)
- [x] Extraction guard: prompt explicitly allows `[]` for fact-neutral queries
- [x] Embedding threshold warning at >100 facts (`EMBEDDING_THRESHOLD` constant)
- [x] N+1 LLM call audit documented in NOTES.md (backfill + dedup patterns)
- [ ] При росте базы фактов (>100) рассмотреть переход на embeddings-based retrieval вместо LLM-фильтрации всего списка
- [ ] При росте до 50+ фактов рассмотреть batch-версию backfill_isolated_relations и dedup

## Phase 8.2: Security & Session Isolation (Stable ✅)
- [x] Session isolation: unique UUID v4 generated in-memory per frontend tab to prevent confirmation race conditions
- [x] API Key Authorization: FastAPI middleware validating `X-API-Key` on `/api/*` routes (with preflight OPTIONS and health check bypass)
- [x] Prompt Injection Guard: automatic XML wrapping of untrusted external content (emails and calendar)
- [x] Network Bind: host `0.0.0.0` architectural decision documented and protected via API-Key auth
- [x] Mobile responsive layout fix: memory legend and node details converted into elegant bottom sheets on mobile devices (<640px)

## Phase 9: Unified Dashboard & Chat UI (Stable ✅)
- [x] Dashboard Navigation Shell: AppShell layout component with a left vertical sidebar on desktop and bottom navigation tabs on mobile
- [x] Chat UI: full-featured interactive chat interface supporting session isolation, loading states, and inline confirmation controls
- [ ] Calendar Page: future dashboard page for direct calendar event management
- [ ] Mail Page: future dashboard page for reading/searching mail inboxes
- [ ] Finance Page: future dashboard page for financial transactions log and overview
- [ ] Countdowns Page: future dashboard page for deadliness/timer lists

## Open Technical Debt (Backlog)
- [ ] DRY refactoring: consolidate fetch, loading state, and error handling in frontend components (graph, review, consolidation) into a reusable hook/service
- [ ] Accessibility (A11y) improvements: add standard ARIA labels, tab index controls, and keyboard navigation support to frontend components

## Backlog / Future Ideas
- [ ] Языковой тренажёр для Ausbildung (English/German) — детали в NOTES.md, три подхода рассмотрены, старт с варианта 1 (spaced repetition словарь)


