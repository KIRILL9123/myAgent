# Mira — Long-Term Roadmap and Product Vision

> **Responsibility**: Complete long-term vision, phased roadmap, and product direction.
> For runtime and current implementation guidance, see [ARCHITECTURE.md](ARCHITECTURE.md) and [OPERATIONS.md](OPERATIONS.md).
> For the active work cycle, see [BACKLOG.md](BACKLOG.md).
> For the complete comparison with the product vision brief, see [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md).

---

## A. North Star

**Mira is a local-first Personal Operating System — a Personal Chief of Staff for one person.**

The long-term system will:

- Understand the user's state, preferences, history, goals, commitments, and documents.
- Reason across memory, email, calendar, finance, files, projects, and other domains.
- Proactively surface important information without becoming noisy.
- Propose actions with provenance — every conclusion traceable to supporting evidence.
- Execute only inside deterministic permission boundaries.
- Require explicit human approval for all high-impact actions.
- Remain local-first and privacy-preserving where practical.
- Improve through controlled, backlog-driven engineering workflows with automated validation and human review.

---

## B. Personal OS Data Model

The long-term system conceptually manages eight categories of structured knowledge:

| Type | Description |
|---|---|
| **Facts** | Stable, approved beliefs about the user (preferences, skills, habits) |
| **Episodes** | Recorded events or conversations with temporal context |
| **Artifacts** | Binary files, documents, PDFs — separate from structured state |
| **Plans** | Sequences of intended actions toward a goal |
| **Commitments** | Obligations the user has made or accepted, with lifecycle tracking |
| **Events** | Calendar entries with temporal anchoring |
| **Decisions** | Explicit choices made by the user, with supporting rationale |
| **Evidence** | Raw source material supporting a fact, decision, or commitment |

### Storage architecture principles

- **SQL is authoritative for structured state.** SQLite is the source of truth for facts, commitments, events, decisions, and their relations.
- **Vector search is for retrieval, not truth.** Embeddings and similarity indices accelerate lookup; they do not replace structured records.
- **Binary files and artifacts remain separate** from structured state. The document vault is distinct from the memory layer.
- **Provenance connects conclusions to evidence.** Every derived fact, commitment, or decision should carry a reference trail back to its source material.

---

## C. Unified Approval Control Plane

The long-term design converges on a single **Unified Approval Inbox / Approval Control Plane** as the gateway for all high-impact proposed changes. The current implementation projects memory facts, commitments, subscription proposals, document-derived proposals, RED actions and sandbox applies into shared approval records, API and web surfaces; full event history and policy unification remain future work.

This control plane handles:

- Memory fact approvals
- RED tool action confirmations
- Commitment activation proposals
- Subscription proposals
- Document-derived task/event proposals
- Sandbox-apply proposals
- Future self-improvement code change proposals
- Other high-impact state changes requiring human review

### Conceptual flow

```
AI proposal
  → Approval Center (unified record store)
  → User: approve / reject / edit
  → Deterministic policy/permission check
  → Execution
  → Audit log with full provenance
```

Implementation note: Telegram and the web dashboard may share the same underlying approval records. This is an architectural concept; it does not prescribe a single UI implementation.

---

## D. Roadmap Phases

### Phase 1 — Safety, Infrastructure, and Code Quality

*Prerequisites for all future work. The system must be safe to test, safe to run, and maintainable.*

#### Current hardening cycle — closed 2026-08-05

The documentation reconciliation and bounded reliability hardening cycle is
closed. It is recorded in [RELIABILITY_AUDIT_2026-08-04.md](decisions/RELIABILITY_AUDIT_2026-08-04.md).
The first Goals/Projects/Decision Journal slice is implemented and recorded in
[BACKLOG.md](BACKLOG.md) and [GOALS_PROJECTS_DECISION_JOURNAL.md](design/GOALS_PROJECTS_DECISION_JOURNAL.md).
The next product cycle is projection polish in Today and Action Center; see
[BACKLOG.md](BACKLOG.md).
No new top-level product domain is scheduled until its acceptance criteria are
verified. This is intentionally scoped for Mira as a personal local-first system.

- [x] Dry-run / side-effect isolation (see [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md))
- [x] Pydantic tool argument validation (see [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md))
- [x] SQLite backup and restore (see [OPERATIONS.md](OPERATIONS.md))
- [x] Fix known contract inconsistencies:
  - `scheduled_tasks.py` parses connector outputs as JSON strings (connectors return Python objects)
  - `mail_connector.py` `send_email()` uses `{"error": ...}` instead of `{"status": "error", ...}`
  - Missing permissions for countdown tools in the former permission matrix
  - `delete_countdown` should have explicit permission level
- [x] Set up test runner (pytest) + CI
- [x] Type hints across all backend modules
- [x] Regression tests for RED action boundaries and side-effect isolation
- [x] Fact confidence / temporal validity / provenance — audit + metadata + expired filter + PATCH endpoint (see [design/MEMORY_EVOLUTION.md](design/MEMORY_EVOLUTION.md))
- [x] Add token counting to prevent silent context window overflow
- [x] Fix N+1 LLM calls in memory layer (batch dedup for fact extraction, batch relations for backfill)
- [x] Observability foundation: correlation IDs, structured telemetry events, model/port health checks and Dashboard status widget

### Phase 2 — Model Abstraction Layer

*Model coupling is the biggest architectural debt. Every model-dependent file imports `chat_with_ollama` directly.*

- [x] Unified provider-neutral chat layer in `backend/app/agent/llm.py`
- [x] Ollama and OpenAI-compatible provider implementations in the unified layer
- [ ] `MLXProvider` implementation (Apple Silicon native, for future production)
- [ ] `ModelRegistry` — typed role-to-provider/model mapping
- [ ] Model roles: `main_reasoning`, `extractor`, `fast_classifier`, `embeddings`
- [x] Replace direct model calls with the unified `llm.chat` facade:
  - `orchestrator.py` (main chat + tool calling)
  - `scheduled_tasks.py` (morning summary)
  - `memory_service.py` (fact filtering + consolidation)
  - `fact_extractor.py` (extraction + dedup)
  - `relation_builder.py` (relation suggestions)
- [x] Model configuration in `.env` / config (per-role model selection, provider choice)
- [x] Fallback model support (if main model is unavailable → try fallback → error)
- [x] Regression tests for Ollama and OpenAI-compatible fallback paths

**Expected benefit**: Swap models by changing config, not code. Run different models for different tasks. Add remote APIs without business logic changes.

### Phase 3 — Centralized Tool Infrastructure

*Tool definitions are duplicated in 3+ places. A tool registry eliminates this.*

- [x] Centralized Tool Registry (schema, Pydantic model, permission level, dispatch handler, audit metadata in one place)
- [x] Replace inline `AVAILABLE_TOOLS` in `orchestrator.py` with registry-driven generation
- [x] Add a CI drift check so every registered tool has matching schema, validation, permission and dispatch coverage
- [ ] Standardize all tool return contracts to `{"status": "success"|"error", ...}`
- [x] Auto-generate OpenAI-compatible tool definitions from Pydantic models through the central registry
- [ ] Shadow mode for new tools (dry-run exists, but intent comparison reports are not implemented)
- [ ] `ExecutionMode` fully integrated (DRY_RUN → return `would_do` payloads)

### Phase 4 — Domain Services

*Extract complex domains into maintainable services without turning them into agents.*

**Commitment Tracker**
- [x] Commitment entity lifecycle: PROPOSED → ACTIVE → COMPLETED / CANCELLED / EXPIRED
- [x] SQLite-backed commitment entity with provenance, owner, source and reminder fields
- [x] Approval-backed API and lifecycle event history
- [x] Deadline expiry review operation
- [x] Commitment extraction proposals from email (chat extraction remains a follow-up)
- [x] Calendar / deadline linkage for commitments (explicit event links; events never auto-complete commitments)
- [x] Commitment reminders via Telegram
- [x] Commitment expiry and review flow
- [x] Task flow v1 through Chat and Telegram: create active personal tasks, list, reschedule, complete, cancel, and explicitly link a calendar event (see [design/TASK_FLOW.md](design/TASK_FLOW.md))

**Subscription Tracker**
- [x] Separate SQLite entity for trials and recurring subscriptions with provenance
- [x] Email-derived proposals with deduplication and explicit user approval
- [x] Manual subscription entry and cancellation/stop-tracking state
- [x] Trial-end / next-charge dates and configurable reminder lead time
- [x] Telegram reminders for approved active subscriptions
- [ ] Search historical mail and project subscription signals into Calendar / Personal State
- [x] Unified Approval Control Plane projection for subscription proposals

**Personal State Engine**
- [x] Deterministic read-only state snapshot aggregating commitments, subscriptions, deadlines and monthly finance
- [x] Today Overview v2: one cached `/dashboard` projection for schedule, active tasks, deadlines, attention items and next actions (see [design/TODAY_OVERVIEW.md](design/TODAY_OVERVIEW.md))
- [x] Priority signals for overdue items, near-term charges and pending approvals
- [x] Dashboard widget and full `/state` view
- [x] Morning summary receives the current state signal
- [x] Daily state snapshots, history and deterministic "State of Me" report
- [x] Unified Action Center read model for priorities, deadlines, reminders and approval-required actions (see [design/ACTION_CENTER.md](design/ACTION_CENTER.md))
- [x] Action Center v1.1: read/unread, snooze, dismiss, and Commitment complete/reschedule controls shared by Today and Notification Center (see [design/ACTION_CENTER.md](design/ACTION_CENTER.md))
- [x] Shared temporal context for local-day boundaries, countdowns, Action Center, Personal State and Telegram delivery
- [ ] Calendar and email state history
- [x] Decision Journal and project/goal hierarchy — bounded v1 implemented;
  projection polish remains
  the bounded first slice from [GOALS_PROJECTS_DECISION_JOURNAL.md](design/GOALS_PROJECTS_DECISION_JOURNAL.md)

**Memory Evolution**
- [x] Provenance and Evidence Bundle contract documented with source, locator, derivation, reference-time and approval rules; normalized persistence and user-visible citations remain future work
- [ ] `last_confirmed_at` field
- [ ] Temporal validity window (`valid_from`, `valid_to`)
- [ ] Decay scoring (advisory only)
- [ ] Auto-weight retrieval by confidence + recency

**Document Vault / RAG v1**
- [x] Separate local artifact storage with metadata, hashes and archive state
- [x] Text/Markdown/CSV/JSON/HTML/PDF extraction and bounded chunking
- [x] SQLite FTS5 retrieval with document provenance and untrusted-content wrapping
- [x] Chat context injection for document-related questions and `/documents` management UI
- [ ] Semantic embeddings, OCR for scans and reranking (OCR design reference: [Paperless-ngx audit](decisions/OSS_AUDIT_2026-08-04.md))
- [x] High-confidence document obligation/date candidates can create task or calendar proposals through Approval Center; OCR, semantic extraction, embeddings, reranking and document-to-memory proposals remain future work

**Agent Brain — ideas inspired by Waku Agent**
- [x] Retrieval Gate v1: deterministic pre-retrieval routing skips irrelevant operational turns, records the reason in `agent_turn` and fails open if the gate itself errors; semantic/LLM routing remains future work
- [x] Procedural Memory / Skills v1: separate approved workflows with deterministic trigger selection, draft/approved/disabled lifecycle and Approval Center integration; richer editing and semantic selection remain future work
- [x] Deterministic Evaluation + Release Gate v1: backend/frontend checks are reproducible, fail the command on regression and persist verdict history; optional LLM-judge quality checks remain future work
- [x] Per-turn Agent Trace v1: aggregate turn event records loop iterations, tool calls, latency, memory usage, token estimates and final outcome; gate decisions remain future work

**Notifications**
- [x] Quiet hours configuration
- [x] Notification budget and priority scoring
- [x] Notification coalescing and deduplication for Telegram delivery
- [x] Shared Action Center delivery layer for Telegram
- [x] Notification preferences UI; future mobile-client delivery remains planned

**Runtime reliability**
- [x] Shared async I/O boundary for IMAP, CalDAV, document ingestion/search, State/Action Center reads, subscription scans and morning summaries
- [x] Confirmation audit hardening and channel identity enforcement: atomic claim/cancel, Telegram action-id binding, failure persistence and replay/race regression coverage
- [x] Safety/test hygiene: local dry-run example defaults, explicit manual live-script boundary, credential-safe diagnostics and protected pytest discovery

**Calendar runtime contract**
- [x] Route all calendar consumers through the configured provider service; remove direct CalDAV bypasses from Assistant, Personal State, scheduled summaries, and notification delivery
- [x] Expand local recurrence instances for future calendar ranges and reminders
- [x] Preserve the complete calendar tool contract across LLM schema, Pydantic validation, Chat, and Telegram
- [x] Smart Scheduling v1: shared read-only free-slot search with TemporalContext and approved Memory preferences (see [design/SMART_SCHEDULING.md](design/SMART_SCHEDULING.md))

**Cross-domain**
- [x] Calendar × Commitments conflict detection v1: read-only event/event and deadline/event warnings in Calendar, Today, Action Center, Chat and Telegram (see [design/CONFLICT_DETECTION.md](design/CONFLICT_DETECTION.md))
- [x] Calendar × Memory conflict detection v1.1: explicit approved preference checks and pre-save warning
  (implemented 2026-08-04; see [design/CONFLICT_DETECTION.md](design/CONFLICT_DETECTION.md))
- [ ] Receipt → Expense proposal (agent notices a purchase receipt and proposes adding it to Finance)

### Phase 5 — Personal State and RAG (Only If Justified)

*These features should be built only if Phase 4 demonstrates a concrete need. Do not build speculatively.*

**Personal State Engine**
- [ ] Consumes commitment, memory, and calendar signals
- [x] Decision Journal (explicit record of choices with rationale; approved
  proposal: [GOALS_PROJECTS_DECISION_JOURNAL.md](design/GOALS_PROJECTS_DECISION_JOURNAL.md))
- [x] Project entities: Goals → Projects → Tasks → Commitments hierarchy (task
  flow v1 currently remains a Commitment-backed projection; UX references:
  [Super Productivity/Vikunja audit](decisions/OSS_AUDIT_2026-08-04.md))
- [ ] Nightly "State of Me" summary
- [ ] Contradiction-aware retrieval (prefer latest human-confirmed facts when conflicts exist)

**Document / RAG Layer**
- [x] Document Vault v1 — distinct from Memory Facts, with local artifacts, extraction, chunks and FTS5 retrieval
- [x] Explicit Document Vault links to commitments, calendar events, and subscriptions — relation metadata only; see [`docs/design/DOCUMENT_LINKS.md`](design/DOCUMENT_LINKS.md)
- [ ] Local embeddings (via Model Registry, role: `embeddings`)
- [ ] Local vector store (Chroma or Qdrant)
- [ ] Hybrid SQL + vector retrieval
- [x] Provenance and document source cards in answers (lexical retrieval; semantic citations remain planned)
- [x] PDF text ingestion (OCR for scans remains planned)

**Host and Operations Foundation**
- [x] Read-only host diagnostics for CPU, RAM, disk and processes
- [x] Computer Control v1 capability contract with allowlisted URL/path opening and RED confirmation
- [x] Windows watchdog and user-level Scheduled Task installer
- [x] Healthcheck script and configurable CORS origins for LAN development
- [ ] HTTPS/VPN deployment automation and macOS service adapter
- [x] Document deadline extraction → Calendar suggestions, approval-gated through the existing Action Center
- [x] Document → Commitment proposals, approval-gated with provenance links

### Phase 6 — Selective Multi-Agent Architecture (Only If Justified)

*Do not build multi-agent because it is fashionable. The single orchestrator must prove insufficient first.*

**Criteria for escalation from single orchestrator to multi-agent:**
- System prompt exceeds 8K effective tokens
- Tool count exceeds 25-30
- A domain requires complete containerized isolation (separate model, separate context, separate memory)
- Latency from accumulated context becomes user-visible

**If criteria are met:**
- [ ] Agent Registry (agent_id, capabilities, allowed_tools, required_permissions, model_role)
- [ ] Inter-agent dispatch with permission context inheritance
- [ ] Cross-agent audit trail
- [ ] Max delegation depth (2 levels max)
- [ ] Circuit breaker for recursive / infinite loops

### Phase 7 — External World and Host Capabilities (Security-Gated)

*These capabilities expand the agent beyond local application data. They must remain
read-only-first, provenance-aware, budgeted and approval-gated for any side effect.*

**Weather and internet access**
- [x] Add a weather connector with city/location resolution, current conditions and forecast
- [x] Include provider, observation time, timezone, units and source in every weather response
- [x] Add provider timeout and graceful degraded-mode behavior
- [x] Define and implement the first controlled web-access layer with domain policy, response/request limits and HTTP-first retrieval
- [x] Run an initial Lightpanda-vs-Playwright/Chromium browser-runtime PoC; keep production integration pending external compatibility tests
- [x] Treat web pages and retrieved text as untrusted content; wrap it before the model sees it
- [x] Store provenance and retrieval timestamps for externally sourced answers
- [x] Add Web Research price evidence extraction, RU product-query normalization for Germany, and explicit 403-to-search-snippet fallback
- [ ] Add robots-policy coverage, stronger per-session budgets and broader browser compatibility tests

**Host computer control**
- [x] Read-only host diagnostics: CPU, RAM, disks, process count and top processes
- [x] Code Sandbox MVP: bounded workspace, safe relative paths, explicit write confirmation, Docker runner, allowlisted checks, diff/baseline preview and approval-gated conflict-safe apply (see [design/CODE_SANDBOX.md](design/CODE_SANDBOX.md))
- [ ] Define capability levels: read-only diagnostics → preview/dry-run → approved action
- [ ] Add scoped capability tokens, richer sandbox audit history, emergency stop and adversarial evaluation coverage
- [x] Docker execution boundary with no network, read-only root, dropped capabilities and resource limits; VM-level isolation and broader adversarial coverage remain planned
- [ ] Implement a Windows 11 adapter first (processes, services, files and selected apps)
- [ ] Implement a macOS adapter later for Mac Studio/Mac mini (launchd, processes, files and selected apps)
- [ ] Add cross-platform capability contracts so the agent does not depend on OS-specific commands
- [ ] Add adversarial tests for prompt injection, path traversal, destructive commands and privilege escalation

---

## E. Later / Experimental

These are worth preserving but not scheduled. Do not plan implementation time for them.

### Selected Product Ideas Preserved for Future Scheduling

The selected ideas are mirrored in [BACKLOG.md](BACKLOG.md). Checked items are retained
as delivery history; unchecked items are not scheduled until a new active cycle is opened.
Notification Center v1 and v1.1 are implemented as Action Center projections.

- [x] Subscription → Finance recurring-transaction proposals, always approval-gated for supported monthly EUR subscriptions; Finance now also has native grouped currencies and weekly/monthly/yearly projections (2026-08-04; see [FINANCE_MODEL.md](design/FINANCE_MODEL.md)).
- Security-backlog reminders and a monthly security report.
- Focus mode layered on top of Quiet Hours.
- Archive/recovery instead of destructive deletion.
- Document links to Personal State and richer evidence views.
- OCR for scans and photos.
- Version-to-version document comparison.
- Clearly marked unverified external data with provenance and freshness.
- [x] Unified Notification Center v1.1 for approvals, reminders, errors and proposals, including projection lifecycle and Commitment actions.
- [x] Mobile four-action mode for Chat, Tasks, Notifications and File Upload; remaining sections live under «Ещё».
- [ ] Safe cleanup of temporary sandbox, log, upload and cache artifacts.
- [x] Persistent error reporting with correlation context and a fix lifecycle: new → fixing → fixed → verified → closed.

- **Self-Improving Agent** — requires ALL safety phases complete, plus sandbox infrastructure. Earliest: after Phase 5.
- **Ausbildung / Language Trainer** — spaced repetition, OCR, generative exercises. Valuable but orthogonal to the core architecture.
- **Home Assistant integration** — sensor graphs, basic device control via chat (postponed; low device count)
- **Deeper email intelligence** — thread grouping, unread badge, advanced spam classification
- **Approval-based email auto-filing rules** — user-configured, not autonomous
- **GitHub integration** — open issues and PRs in morning summary
- **Finance intelligence** — "Can I afford X?" answers based on real Finance logs
- **Voice in web chat** — microphone button using local whisper.cpp (Telegram voice already works)
- **Local Text-to-Speech** — Kokoro or Piper TTS for agent response audio
- **Interactive dashboard widgets** — drag-and-drop resize
- **UI aesthetics evolution** — Glassmorphism, View Transitions API

---

## F. Explicit Non-Goals

The following are out of scope by design:

- Generic multi-tenant SaaS architecture
- Plugin marketplace infrastructure
- Full BPM/workflow engine without a concrete, justified need
- Unrestricted shell or code execution in production
- Unsupervised production self-modification
- Autonomous high-impact financial or communication actions without explicit human approval
- Multi-agent architecture without demonstrated need
- Over-abstraction before understanding real usage patterns

---

## G. Architectural Principles

1. **Model abstraction before model diversity.** Do not add a second model provider until the abstraction layer exists.
2. **Safety before features.** Do not add new domains (Commitments, RAG) until dry-run and validation exist.
3. **Services before agents.** Default to a service/module. Only escalate to an agent when isolation boundaries justify it.
4. **Data protection before schema changes.** Backup/restore must exist before any new schema-migrating feature.
5. **The LLM never controls permissions.** Enforced in deterministic Python code, not in prompts.
6. **External content is untrusted.** Email, calendar events, documents — always wrap in `<untrusted_external_content>`.
7. **Self-improvement must remain sandboxed.** Never modify production code, never bypass approval.
