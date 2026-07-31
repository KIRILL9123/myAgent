# myAgent — Long-Term Roadmap and Product Vision

> **Responsibility**: Complete long-term vision, phased roadmap, and product direction.
> For runtime and current implementation guidance, see [ARCHITECTURE.md](ARCHITECTURE.md) and [OPERATIONS.md](OPERATIONS.md).
> For the active work cycle, see [BACKLOG.md](BACKLOG.md).
> For the complete comparison with the product vision brief, see [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md).

---

## A. North Star

**myAgent is a local-first Personal Operating System — a Personal Chief of Staff for one person.**

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

The long-term design converges on a single **Unified Approval Inbox / Approval Control Plane** as the gateway for all high-impact proposed changes. A first implementation now projects memory facts, commitments and RED actions into a shared approval record, API and web center; full event history and policy unification remain future work.

This control plane handles:

- Memory fact approvals (currently implemented in isolation)
- RED tool action confirmations (currently implemented in isolation)
- Commitment activation proposals
- Document merge/extraction proposals
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

- [x] Dry-run / side-effect isolation (see [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md))
- [x] Pydantic tool argument validation (see [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md))
- [x] SQLite backup and restore (see [OPERATIONS.md](OPERATIONS.md))
- [x] Fix known contract inconsistencies:
  - `scheduled_tasks.py` parses connector outputs as JSON strings (connectors return Python objects)
  - `mail_connector.py` `send_email()` uses `{"error": ...}` instead of `{"status": "error", ...}`
  - Missing permissions for countdown tools in `tool_permissions.json`
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

- [ ] Centralized Tool Registry (schema, Pydantic model, permission level, dispatch handler, audit metadata in one place)
- [ ] Replace inline `AVAILABLE_TOOLS` in `orchestrator.py` with registry-driven generation
- [ ] Standardize all tool return contracts to `{"status": "success"|"error", ...}`
- [ ] Auto-generate OpenAI-compatible tool definitions from Pydantic models
- [ ] Shadow mode for new tools (log intent without executing)
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

**Memory Evolution**
- [ ] Provenance bundle (source type, source ref, extractor metadata)
- [ ] `last_confirmed_at` field
- [ ] Temporal validity window (`valid_from`, `valid_to`)
- [ ] Decay scoring (advisory only)
- [ ] Auto-weight retrieval by confidence + recency

**Notifications**
- [ ] Quiet hours configuration
- [ ] Notification budget and priority scoring
- [ ] Notification coalescing (batch low-priority alerts)

**Cross-domain**
- [ ] Calendar × Memory conflict detection (flag when new event conflicts with known preferences)
- [ ] Receipt → Expense proposal (agent notices a purchase receipt and proposes adding it to Finance)

### Phase 5 — Personal State and RAG (Only If Justified)

*These features should be built only if Phase 4 demonstrates a concrete need. Do not build speculatively.*

**Personal State Engine**
- [ ] Consumes commitment, memory, and calendar signals
- [ ] Decision Journal (explicit record of choices with rationale)
- [ ] Project entities: Goals → Projects → Tasks → Commitments hierarchy
- [ ] Nightly "State of Me" summary
- [ ] Contradiction-aware retrieval (prefer latest human-confirmed facts when conflicts exist)

**Document / RAG Layer**
- [ ] Semantic Document Vault — distinct from Memory Facts
- [ ] Local embeddings (via Model Registry, role: `embeddings`)
- [ ] Local vector store (Chroma or Qdrant)
- [ ] Hybrid SQL + vector retrieval
- [ ] Provenance and citations in answers
- [ ] PDF / scan ingestion
- [ ] Document deadline extraction → Calendar suggestions
- [ ] Document → Commitment proposals

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
- [ ] Define capability levels: read-only diagnostics → preview/dry-run → approved action
- [ ] Add explicit user approval, scoped capability tokens, audit events and emergency stop
- [ ] Sandbox process, filesystem and network access; deny by default
- [ ] Implement a Windows 11 adapter first (processes, services, files and selected apps)
- [ ] Implement a macOS adapter later for Mac Studio/Mac mini (launchd, processes, files and selected apps)
- [ ] Add cross-platform capability contracts so the agent does not depend on OS-specific commands
- [ ] Add adversarial tests for prompt injection, path traversal, destructive commands and privilege escalation

---

## E. Later / Experimental

These are worth preserving but not scheduled. Do not plan implementation time for them.

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
