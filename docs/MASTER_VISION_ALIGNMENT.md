# Master Vision Alignment

This document maps the Master Vision & Ideas brief to the current project reality.
It is the canonical checklist for deciding whether an idea is implemented, planned,
or deliberately deferred. An item marked **planned** is not available in the product yet.

## Product direction

Mira is a local-first Personal Operating System / Personal Chief of Staff. The chat
is an interface, not the product itself. The long-term outcome is a controlled system
that understands personal knowledge, current state, obligations, decisions, documents,
and priorities while requiring human approval for high-impact actions.

## Coverage matrix

| Vision area | Current status | Canonical location / next step |
|---|---|---|
| Memory facts and approval | **Implemented** | `backend/app/memory/*`, Memory UI |
| Retrieval Gate | **Implemented v1** | `backend/app/memory/retrieval_gate.py` skips irrelevant operational turns, logs decision/reason in `agent_turn` and fails open on gate errors; semantic routing remains planned |
| Procedural memory and skills | **Implemented v1** | `backend/app/memory/skill_service.py` stores separate workflows, selects approved skills deterministically and routes user-created skills through the Approval Center; semantic selection and richer editing remain planned |
| Temporal validity, confidence, provenance metadata | **Partially implemented** | `docs/design/MEMORY_EVOLUTION.md`; add source references and user-visible citations |
| Fact decay and reconfirmation | **Planned** | Memory Evolution backlog |
| Poisoned-memory quarantine | **Planned** | Add contradiction/review state before deletion |
| SQL-backed knowledge graph | **Partially implemented** | Fact relations exist; entity types and broader links remain planned |
| Document Vault and document RAG | **Implemented v1** | `backend/app/documents/*`, `/api/documents`, FTS5 chunks, explicit domain links, approval-gated task/event proposals, and `/documents` UI; embeddings, OCR, semantic extraction and reranking remain planned |
| Document deadlines and task/event proposals | **Implemented v1** | High-confidence obligation/date candidates enter the shared Approval Center; approval creates an existing Commitment or Calendar event with provenance |
| Document-to-memory proposals | **Planned** | Future approval-gated extraction into Personal State or Memory |
| Evidence-based answers and citations | **Partially implemented** | Web source cards plus document names/chunk provenance are exposed in chat; the Evidence Bundle contract is documented, while normalized persistence, fact/email citations and richer quote spans remain planned |
| Personal State Engine | **First persistent layer + Today Overview v2 implemented** | Deterministic snapshot, daily history, State of Me report, priority signals, unified `/dashboard` Today projection and morning-summary input; projects, decisions and policy-driven notifications remain |
| Goals → Projects → Tasks → Actions | **Implemented v1** | Goals, Projects and optional `commitments.project_id` are implemented without replacing Commitment-backed tasks; compact `/commitments` tabs and shared Chat/Telegram tools are live |
| Commitment Tracker | **Core + task flow v1 implemented** | Commitment Center, approval-gated email proposals, Chat/Telegram task commands, explicit calendar links, Today/Action Center projections and Telegram reminders; project hierarchy v1 links existing tasks without duplicate state |
| Subscription Tracker | **MVP + unified approvals implemented** | `/subscriptions`, IMAP unread-email proposals, provenance, shared `SUBSCRIPTION` approvals, reminders and manual entry; historical-mail search, Calendar/Personal State links and provider cancellation workflows remain |
| Decision Journal | **Implemented v1** | Structured Knowledge records with provenance, rationale, alternatives and review status in `/memory`; no new top-level route |
| Calendar intelligence | **Core parity + conflict v1.1 + Smart Scheduling v1 implemented** | Calendar UI and provider selection share `calendar_service.py` across Assistant, Personal State, notifications and scheduled summaries; local recurrence, Calendar × Commitments checks, explicit approved Memory preference checks, read-only free-slot proposals and pre-save confirmation are covered; richer density intelligence remains |
| Email threading and importance detection | **Planned** | Add thread grouping, importance, deadlines and action extraction |
| Email → Commitment | **Implemented** | Approval-gated proposals from analyzed email content |
| Receipt → Expense proposal | **Planned** | Approval-gated Finance proposal |
| Email auto-filing | **Planned** | Shadow mode → approval → automation |
| Finance budget advisor and proactive alerts | **Planned** | Balance, recurring costs, goals and spending trend analysis |
| Chief of Staff experience | **Vision / partially supported** | Morning summary, Today Overview and Personal State provide the first synthesis; richer conversational planning remains |
| Daily and nightly state briefs | **Partially implemented** | Morning summary exists; nightly State of Me remains planned |
| Proactive agent | **Partially implemented** | Scheduler and Telegram exist; trigger scoring, quiet hours and budgets remain |
| Quiet hours, notification budget and Telegram coalescing | **Implemented v1** | `/api/notifications/preferences`, Action Center delivery policy and deduplication; interrupt hierarchy and mobile preferences remain |
| Unified Approval Control Plane | **v1 implemented** | Unified approval projection, API and web center cover memory facts, commitments, subscription proposals, document proposals, sandbox applies and RED actions; deeper event history and policy unification remain planned |
| Autonomy levels by domain | **Planned policy** | Formalize levels 0–5 and per-domain configuration |
| Capability tokens | **Planned security feature** | Time-, action- and payload-scoped authorization |
| Evaluation framework and regression pack | **Implemented v1** | `python dev-tools/release_gate.py` runs deterministic backend/frontend checks and persists verdict history; optional LLM judge remains planned |
| Per-turn agent trace | **Implemented v1** | `agent_turn` aggregate includes memory, loop, tool, latency, token estimate and outcome metadata; expose gate decision and richer cost policy later |
| Shadow mode | **Partially implemented** | Dry-run exists; add intent observation and comparison reports |
| Self-improvement workflow | **MVP implemented / hardening pending** | Bounded Code Sandbox, Docker runner, agent tools, explicit write confirmation, allowlisted checks, diff/baseline preview, approval-gated apply and `/sandbox` UI; broader evaluation/history remain future |
| Central Tool Registry | **Implemented v1** | `backend/app/agent/tool_registry.py` owns schema generation, Pydantic validation, permissions, handlers and audit metadata; `dev-tools/check_tool_registry.py` checks drift |
| Pydantic tool validation | **Implemented** | `backend/app/agent/tool_models.py` |
| Audit log | **Implemented v1 / hardening pending** | Tool audit and correlation IDs exist; richer provenance and durable event history remain |
| Durable event/job log | **Planned** | Separate event history from operational logs |
| Sleep-aware bootstrap reconciliation | **Planned** | Startup checks for missed jobs and stale integrations |
| Backup and disaster recovery | **Partially implemented** | SQLite backup/restore exists; add encrypted config/document strategy and tested restore runbook |
| Versioned migrations | **Implemented v1 / hardening pending** | Numbered SQLite migrations exist; migration parsing, foreign-key enforcement and rollback verification remain |
| Observability | **v1 implemented** | Correlation IDs, structured SQLite/JSONL events, per-turn trace, backend/model health and Dashboard status widget; token budgets and richer metrics remain planned |
| Cost and latency budgets | **Planned** | Per-request time, model-call, tool-call and token budgets |
| Model Router | **Partially implemented** | Unified `llm.py` provider layer, role config and fallback exist; typed role routing and embeddings remain planned |
| Weather and forecast access | **Implemented** | Read-only Open-Meteo connector, city resolution, current/5-day forecast, source timestamp and structured chat card |
| Controlled internet access | **v1 implemented / hardening pending** | Read-only web search/fetch with public-network checks, limits, cache, provenance, untrusted-content wrapping and Lightpanda/Chromium fallback; robots and stronger budgets remain planned |
| Host computer control | **Partially implemented / security-gated** | Read-only diagnostics and allowlisted URL/path opening behind RED confirmation exist; process, service, file and broader OS adapters remain planned |
| Hybrid retrieval | **Planned** | SQL filters → vector retrieval → reranking → LLM |
| Adversarial security testing | **Planned** | Corpus for prompt injection, poisoned memory and malicious tool arguments |
| Security model | **Partially implemented** | API auth, deny-by-default permissions, untrusted content wrapping, RED confirmations |
| Sandboxed diagnostics | **v1 implemented** | Read-only backend/model health, ports, CPU, memory, disk and top-process diagnostics; Computer Control v1 adds allowlisted URL/path opening behind RED confirmation; process control remains planned |
| Self-improvement sandbox | **MVP implemented / hardening pending** | `docs/design/CODE_SANDBOX.md`; Docker isolation, workspace checks, diff/baseline preview, conflict-safe backup/apply and UI exist, while broader evaluation and task history remain planned |
| Ausbildung learning system | **Deferred** | Separate learning module with RAG, flashcards, tests and progress |
| Home Assistant | **Deferred** | Long-term integration; not part of the current cycle |
| Personal ontology versioning | **Planned** | Version entity, relation and category types with migrations |
| Dual-store truth / versioned export | **Planned** | SQLite authority plus encrypted, versioned exports |
| Autonomy ramp-up | **Guiding policy** | Observe → Shadow → Suggest → Approve → Limited autonomy → Expanded autonomy |

## Current implementation reality

The project already has a strong foundation: FastAPI, local model serving, chat
orchestration, calendar and mail connectors, Telegram, Finance, countdowns, memory
approval and relations, dry-run boundaries, Pydantic tool validation, backups, a React
dashboard, a shared calendar provider service, a central temporal read-model contract,
an explicit async I/O boundary, confirmation audit hardening, safety/test hygiene,
live smoke coverage, Calendar × Commitments plus Calendar × Memory conflict
detection, and read-only Smart Scheduling through Chat and Telegram. The next
Calendar gap is richer density and preference modeling before any automatic
scheduling behavior is considered.

Today Overview v2 now gives that foundation a single operational front door:
`/dashboard` reads one cached Personal State snapshot and links back to the
owning Calendar, Commitment, Finance, Mail, and Action Center surfaces.

The largest missing product layers are:

1. Deeper Approval Control Plane policy, event history and cross-domain proposals.
2. Today/Action Center projections for project context and review dates.
3. Deeper Document Vault retrieval: OCR, embeddings, semantic extraction and reranking.
4. Durable domain event history, cost budgets and adversarial evaluation.

## Recommended order

1. Finish remaining deployment hardening: replace local placeholder API keys
   before phone/LAN access, then keep migration checks, durable event history,
   request budgets and adversarial regression tests on the reliability backlog.
2. Polish the implemented Decision Journal and Goals -> Projects -> Tasks
   projections in Today and Action Center.
3. Improve Finance intelligence beyond the now-implemented approval-gated Subscription -> Finance proposal link.
4. Extend Document Vault with OCR, embeddings, semantic extraction and reranking.
5. Only then evaluate selective autonomy, model routing and deeper self-improvement.

## Explicit boundaries

- Facts and commitments remain separate entities with separate lifecycles.
- Documents are artifacts, not memory facts; extraction creates approval proposals.
- SQLite remains authoritative for structured state.
- External content is untrusted input.
- High-impact actions require deterministic permission checks and human approval.
- Self-improvement never changes production directly and never bypasses approval.
- Home Assistant and Ausbildung remain long-term/deferred work, not current priorities.
