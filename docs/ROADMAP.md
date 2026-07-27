# myAgent — Long-Term Roadmap and Product Vision

> **Responsibility**: Complete long-term vision, phased roadmap, and product direction.  
> For what is currently implemented, see [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md).  
> For the active work cycle, see [BACKLOG.md](BACKLOG.md).

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

The long-term design converges on a single **Unified Approval Inbox / Approval Control Plane** as the gateway for all high-impact proposed changes.

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

### Phase 1 — Reliability and Safety Foundation

*Prerequisites for all future automation work.*

- [ ] Dry-run / side-effect isolation (see [DRY_RUN_ARCHITECTURE.md](DRY_RUN_ARCHITECTURE.md))
- [ ] Pydantic tool argument validation (see [TOOL_VALIDATION_PLAN.md](TOOL_VALIDATION_PLAN.md))
- [ ] SQLite backup and restore (see [BACKUP_RESTORE_PLAN.md](BACKUP_RESTORE_PLAN.md))
- [ ] Fact confidence, temporal validity, provenance (see [MEMORY_EVOLUTION.md](MEMORY_EVOLUTION.md))
- [ ] Regression tests for RED action boundaries and side-effect isolation
- [ ] Fix known scheduler/connector contract inconsistencies (see [ARCHITECTURE_STATUS.md](ARCHITECTURE_STATUS.md))
- [ ] Evaluate centralized Tool Registry (see [TOOL_VALIDATION_PLAN.md](TOOL_VALIDATION_PLAN.md))

### Phase 2 — Personal Commitments and Proactive Assistance

*Add obligation tracking and proactive user-facing intelligence.*

- [ ] Commitment Tracker domain (see [domain/COMMITMENT_CONTRACT.md](domain/COMMITMENT_CONTRACT.md))
- [ ] Commitment extraction from chat and email
- [ ] Calendar / deadline linkage for commitments
- [ ] Commitment reminders via Telegram
- [ ] Commitment expiry and review flow
- [ ] Calendar × Memory conflict detection (flag when scheduled time conflicts with known preferences)
- [ ] Receipt → Expense proposal (agent notices a purchase receipt and proposes adding it to Finance)
- [ ] Quiet hours configuration
- [ ] Notification budget and priority scoring
- [ ] Notification coalescing (batch low-priority alerts)

### Phase 3 — Personal State and Decision Intelligence

*Higher-order reasoning across the user's goals, projects, and history.*

- [ ] Personal State Engine (consumes commitment, memory, and calendar signals)
- [ ] Decision Journal (explicit record of choices with rationale)
- [ ] Project entities: Goals → Projects → Tasks → Commitments hierarchy
- [ ] Chief-of-staff daily plan generation
- [ ] Nightly "State of Me" summary (broader than morning summary; covers commitments, goals, decisions)
- [ ] Temporal validity for facts (facts can expire; conflicts resolved via human decision)
- [ ] Contradiction-aware retrieval (prefer latest human-confirmed facts when conflicts exist)

### Phase 4 — Document and Knowledge Layer

*Separate, privacy-respecting document intelligence.*

- [ ] Semantic Document Vault — distinct from Memory Facts
- [ ] Local embeddings (Ollama embeddings or equivalent)
- [ ] Local vector store (Chroma or equivalent)
- [ ] Hybrid SQL + vector retrieval
- [ ] Optional reranking
- [ ] Provenance and citations in answers
- [ ] PDF / scan ingestion
- [ ] Document deadline extraction → Calendar suggestions
- [ ] Document → Commitment proposals (e.g. lease renewal date → commitment with deadline)
- [ ] Optional email indexing with explicit user-controlled retention rules

### Phase 5 — Ausbildung and Learning Intelligence

*Language and technical learning support integrated with the daily workflow.*

- [ ] Ausbildung document and knowledge workspace
- [ ] Spaced repetition vocabulary trainer (Telegram-delivered cards via APScheduler)
- [ ] Study material extraction from documents
- [ ] Learning progress tracking
- [ ] Language learning support (German / English technical vocabulary)
- [ ] Daily generative exercises (translation, gap-fill, mini-dialogue)
- [ ] OCR correction for handwritten notes (requires multimodal model or Tesseract)
- [ ] Clear distinction between authoritative documents and generated study material

### Phase 6 — Controlled Self-Improvement

*The agent proposes changes to its own codebase under strict human oversight.*

> For implementation design detail (Aider diff format, LangGraph state graph, Docker sandbox), see [self_improving_agent.md](self_improving_agent.md).

Design principles (never to be compromised):

- Backlog-driven: only items explicitly in the backlog are candidates.
- Narrow scope: one feature or fix per cycle.
- Isolated branch: changes never go directly to `main`.
- Sandbox execution: tests run in an isolated environment with no external side effects.
- Tests first where practical.
- Automated validation: unit, integration, regression, security, permission, and side-effect checks.
- Structured report delivered to user via Telegram and web.
- Risk classification: low / medium / high impact.
- Human review and manual merge: the human approves before any merge.
- **Never bypass the permission or approval architecture.**
- **Never directly modify `main`.**

---

## E. Cross-Cutting Capabilities

These capabilities span multiple phases and should inform design at each phase:

**Approval and Safety**
- Unified Approval Control Plane (see Section C)
- Provenance and citations for all AI-proposed actions
- Capability tokens / time-limited grants for sensitive operations
- Shadow mode for new tools (log intent without executing)
- Adversarial prompt injection regression corpus (grow from real incidents)
- Regression pack from real failures

**Observability and Reliability**
- Structured correlation IDs across request/tool/audit chain
- Cost, latency, and time budgets per tool call
- Sleep-aware startup reconciliation (Mac sleeps; scheduler must detect missed jobs on wake)
- Evaluation harness / golden scenarios for end-to-end agent behavior

**Notifications**
- Notification priority hierarchy
- Quiet hours configuration
- Notification budget (daily/weekly cap per category)
- Coalescing of low-priority alerts

**Privacy and Backup**
- Encrypted off-machine backups
- Optional encrypted history/export
- Retention policies for all stored data categories

**Model Routing**
- Local model router
- Small models for classification and extraction tasks
- Larger models for multi-step reasoning

---

## F. Later / Experimental

Lower-priority ideas that are worth preserving but not scheduled:

- **Home Assistant integration** — sensor graphs, basic device control via chat (currently postponed; low device count)
- **Deeper email intelligence** — thread grouping, unread badge in navigation, advanced spam classification
- **Approval-based email auto-filing rules** — user-configured, not autonomous
- **GitHub integration** — open issues and PRs in morning summary
- **Finance intelligence** — "Can I afford X?" answers based on real Finance logs; proactive category-limit alerts
- **Language trainer extensions** — see Phase 5 for primary plan
- **More autonomous personal planning** — calendar optimization, energy-aware scheduling
- **Always-on dedicated server** — Raspberry Pi or mini-PC to replace MacBook Air as host
- **Voice in web chat** — microphone button using local whisper.cpp (Telegram voice already works)
- **Local Text-to-Speech** — Kokoro or Piper TTS for agent response audio
- **Interactive dashboard widgets** — drag-and-drop resize (Gridstack)
- **UI aesthetics evolution** — Glassmorphism, View Transitions API

---

## G. Explicit Non-Goals

The following are out of scope by design:

- Generic multi-tenant SaaS architecture
- Plugin marketplace infrastructure
- Full BPM/workflow engine without a concrete, justified need
- Unrestricted shell or code execution in production
- Unsupervised production self-modification (see Phase 6 for the controlled alternative)
- Autonomous high-impact financial or communication actions without explicit human approval
