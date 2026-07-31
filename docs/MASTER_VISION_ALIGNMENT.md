# Master Vision Alignment

This document maps the Master Vision & Ideas brief to the current project reality.
It is the canonical checklist for deciding whether an idea is implemented, planned,
or deliberately deferred. An item marked **planned** is not available in the product yet.

## Product direction

MyAgent is a local-first Personal Operating System / Personal Chief of Staff. The chat
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
| Document Vault and document RAG | **Implemented v1** | `backend/app/documents/*`, `/api/documents`, FTS5 chunks and `/documents` UI; embeddings, OCR and reranking remain planned |
| Document deadlines and document-to-memory proposals | **Planned** | Approval-gated document workflow |
| Evidence-based answers and citations | **Partially implemented** | Web source cards plus document names/chunk provenance are exposed in chat; fact/email citations and richer quote spans remain planned |
| Personal State Engine | **First persistent layer implemented** | Deterministic snapshot, daily history, State of Me report, priority signals, Dashboard/`/state` view and morning-summary input; projects, decisions and policy-driven notifications remain |
| Goals → Projects → Tasks → Actions | **Planned** | Project entities and hierarchy |
| Commitment Tracker | **Core + first integrations implemented** | Commitment Center, email proposals, calendar links and Telegram reminders; Personal State consumption remains |
| Subscription Tracker | **MVP + unified approvals implemented** | `/subscriptions`, IMAP unread-email proposals, provenance, shared `SUBSCRIPTION` approvals, reminders and manual entry; historical-mail search, Calendar/Personal State links and provider cancellation workflows remain |
| Decision Journal | **Planned** | Decision, rationale, alternatives, evidence and status |
| Calendar intelligence | **Partially planned** | Add conflict, density, preference, commitment and project-deadline checks |
| Email threading and importance detection | **Planned** | Add thread grouping, importance, deadlines and action extraction |
| Email → Commitment | **Implemented** | Approval-gated proposals from analyzed email content |
| Receipt → Expense proposal | **Planned** | Approval-gated Finance proposal |
| Email auto-filing | **Planned** | Shadow mode → approval → automation |
| Finance budget advisor and proactive alerts | **Planned** | Balance, recurring costs, goals and spending trend analysis |
| Chief of Staff experience | **Vision / partially supported** | Morning summary exists; Personal State and priority synthesis remain |
| Daily and nightly state briefs | **Partially implemented** | Morning summary exists; nightly State of Me remains planned |
| Proactive agent | **Partially implemented** | Scheduler and Telegram exist; trigger scoring, quiet hours and budgets remain |
| Quiet hours, notification budget and Telegram coalescing | **Implemented v1** | `/api/notifications/preferences`, Action Center delivery policy and deduplication; interrupt hierarchy and mobile preferences remain |
| Unified Approval Control Plane | **v1 implemented** | Unified approval projection, API and web center cover memory facts, commitments, subscription proposals and RED actions; deeper event history and policy unification remain planned |
| Autonomy levels by domain | **Planned policy** | Formalize levels 0–5 and per-domain configuration |
| Capability tokens | **Planned security feature** | Time-, action- and payload-scoped authorization |
| Evaluation framework and regression pack | **Implemented v1** | `python dev-tools/release_gate.py` runs deterministic backend/frontend checks and persists verdict history; optional LLM judge remains planned |
| Per-turn agent trace | **Implemented v1** | `agent_turn` aggregate includes memory, loop, tool, latency, token estimate and outcome metadata; expose gate decision and richer cost policy later |
| Shadow mode | **Partially implemented** | Dry-run exists; add intent observation and comparison reports |
| Self-improvement workflow | **MVP implemented / hardening pending** | Bounded Code Sandbox, Docker runner, agent tools, explicit write confirmation, allowlisted checks, diff/baseline preview, approval-gated apply and `/sandbox` UI; broader evaluation/history remain future |
| Central Tool Registry | **Planned** | Unify schema, handler, permission, validation, risk and audit metadata |
| Pydantic tool validation | **Implemented** | `backend/app/agent/tool_models.py` |
| Audit log | **Partially implemented** | Tool audit exists; add correlation IDs and complete provenance |
| Durable event/job log | **Planned** | Separate event history from operational logs |
| Sleep-aware bootstrap reconciliation | **Planned** | Startup checks for missed jobs and stale integrations |
| Backup and disaster recovery | **Partially implemented** | SQLite backup/restore exists; add encrypted config/document strategy and tested restore runbook |
| Versioned migrations | **Missing / high priority** | Replace ad-hoc `ALTER TABLE` checks with numbered migrations or Alembic |
| Observability | **v1 implemented** | Correlation IDs, structured SQLite/JSONL events, per-turn trace, backend/model health and Dashboard status widget; token budgets and richer metrics remain planned |
| Cost and latency budgets | **Planned** | Per-request time, model-call, tool-call and token budgets |
| Model Router | **Partially implemented** | Unified `llm.py` provider layer, role config and fallback exist; typed role routing and embeddings remain planned |
| Weather and forecast access | **Implemented** | Read-only Open-Meteo connector, city resolution, current/5-day forecast, source timestamp and structured chat card |
| Controlled internet access | **v1 implemented / hardening pending** | Read-only web search/fetch with public-network checks, limits, cache, provenance, untrusted-content wrapping and Lightpanda/Chromium fallback; robots and stronger budgets remain planned |
| Host computer control | **Planned / security-gated** | Add sandboxed diagnostics and narrowly scoped approved actions through OS-specific Windows/macOS adapters |
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
dashboard, a provider abstraction, and live smoke coverage.

The largest missing product layers are:

1. Deeper cross-domain use of the Approval Control Plane, including subscriptions.
2. Personal State history, decisions and project hierarchy.
3. Document Vault / RAG with provenance.
4. Durable observability and event history.

## Recommended order

1. Finish safety and infrastructure: versioned migrations, approval unification,
   observability, request budgets and adversarial regression tests.
2. Add deeper commitment extraction from chat/documents and Personal State consumption.
3. Implement Personal State and daily/nightly state briefs.
4. Add Document Vault / RAG and evidence-based answers.
5. Add Decision Journal, project entities and finance intelligence.
6. Only then evaluate selective autonomy, model routing and self-improvement.

## Explicit boundaries

- Facts and commitments remain separate entities with separate lifecycles.
- Documents are artifacts, not memory facts; extraction creates approval proposals.
- SQLite remains authoritative for structured state.
- External content is untrusted input.
- High-impact actions require deterministic permission checks and human approval.
- Self-improvement never changes production directly and never bypasses approval.
- Home Assistant and Ausbildung remain long-term/deferred work, not current priorities.
