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
| Temporal validity, confidence, provenance metadata | **Partially implemented** | `docs/design/MEMORY_EVOLUTION.md`; add source references and user-visible citations |
| Fact decay and reconfirmation | **Planned** | Memory Evolution backlog |
| Poisoned-memory quarantine | **Planned** | Add contradiction/review state before deletion |
| SQL-backed knowledge graph | **Partially implemented** | Fact relations exist; entity types and broader links remain planned |
| Document Vault and document RAG | **Planned** | Separate artifact storage, parsing/OCR, chunks, embeddings, retrieval, reranking |
| Document deadlines and document-to-memory proposals | **Planned** | Approval-gated document workflow |
| Evidence-based answers and citations | **Planned** | Fact/email/document/chunk provenance in responses |
| Personal State Engine | **Planned** | Aggregate memory, calendar, mail, finance, tasks, projects and commitments |
| Goals → Projects → Tasks → Actions | **Planned** | Project entities and hierarchy |
| Commitment Tracker | **Core + first integrations implemented** | Commitment Center, email proposals, calendar links and Telegram reminders; Personal State consumption remains |
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
| Quiet hours, notification budget, coalescing and interrupt hierarchy | **Planned** | Notification policy service |
| Unified Approval Control Plane | **v1 implemented** | Unified approval projection, API and web center cover memory facts, commitments and RED actions; deeper event history and policy unification remain planned |
| Autonomy levels by domain | **Planned policy** | Formalize levels 0–5 and per-domain configuration |
| Capability tokens | **Planned security feature** | Time-, action- and payload-scoped authorization |
| Evaluation framework and regression pack | **Partially implemented** | `backend/tests`, E2E smoke test; add evaluation corpus and CI gates |
| Shadow mode | **Partially implemented** | Dry-run exists; add intent observation and comparison reports |
| Self-improvement workflow | **Documented, not implemented** | `docs/design/SELF_IMPROVING_AGENT.md`; sandbox and approval pipeline remain future |
| Central Tool Registry | **Planned** | Unify schema, handler, permission, validation, risk and audit metadata |
| Pydantic tool validation | **Implemented** | `backend/app/agent/tool_models.py` |
| Audit log | **Partially implemented** | Tool audit exists; add correlation IDs and complete provenance |
| Durable event/job log | **Planned** | Separate event history from operational logs |
| Sleep-aware bootstrap reconciliation | **Planned** | Startup checks for missed jobs and stale integrations |
| Backup and disaster recovery | **Partially implemented** | SQLite backup/restore exists; add encrypted config/document strategy and tested restore runbook |
| Versioned migrations | **Missing / high priority** | Replace ad-hoc `ALTER TABLE` checks with numbered migrations or Alembic |
| Observability | **Planned** | Structured logs, correlation IDs, traces, latency, tokens and dashboard metrics |
| Cost and latency budgets | **Planned** | Per-request time, model-call, tool-call and token budgets |
| Model Router | **Partially implemented** | Unified `llm.py` provider layer, role config and fallback exist; typed role routing and embeddings remain planned |
| Weather and forecast access | **Planned** | Add a read-only weather connector with location resolution, source/timestamp and graceful provider failure |
| Controlled internet access | **Planned / security-gated** | Add policy-constrained web retrieval with domain allow/deny rules, budgets, provenance and prompt-injection defenses |
| Host computer control | **Planned / security-gated** | Add sandboxed diagnostics and narrowly scoped approved actions through OS-specific Windows/macOS adapters |
| Hybrid retrieval | **Planned** | SQL filters → vector retrieval → reranking → LLM |
| Adversarial security testing | **Planned** | Corpus for prompt injection, poisoned memory and malicious tool arguments |
| Security model | **Partially implemented** | API auth, deny-by-default permissions, untrusted content wrapping, RED confirmations |
| Sandboxed diagnostics | **Planned** | Read-only health, process, CPU, memory and disk diagnostics |
| Self-improvement sandbox | **Planned / deferred** | Branch + isolated environment + tests + evaluation + human approval |
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

1. Unified Approval Control Plane.
2. Unified Approval Control Plane.
3. Personal State Engine.
4. Document Vault / RAG with provenance.
5. Durable observability and event history.

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
