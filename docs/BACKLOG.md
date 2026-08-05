# Backlog

> **Responsibility**: Active work cycle (max 4 items) + future parking lot.  
> The complete long-term vision and phased roadmap belongs in [ROADMAP.md](ROADMAP.md).

---

## Completed Reliability Cycle — 2026-08-05

The cycle is intentionally bounded for the personal local-first deployment. The
full findings and acceptance criteria are in
[RELIABILITY_AUDIT_2026-08-04.md](decisions/RELIABILITY_AUDIT_2026-08-04.md).

- [x] Reconcile stale and contradictory documentation statuses (2026-08-04; see
  [RELIABILITY_AUDIT_2026-08-04.md](decisions/RELIABILITY_AUDIT_2026-08-04.md)).
- [x] Add regression coverage for FK enforcement, confirmation expiry, bounded
  document uploads, concurrent dedupe, and notification delivery bookkeeping.
- [x] Implement the first bounded safety fixes and align CI with the full release gate
  (workflow updated 2026-08-04; remote Actions run remains the final environment check).
- [x] Finish remaining contract fixes, add the cross-domain smoke test, and
  reassess the product backlog before opening Decision Journal and Projects.

## Completed Product Cycle — 2026-08-05

This cycle opens the next product layer without creating another top-level
mini-application. The full placement and lifecycle proposal must land before
schema or UI work.

- [x] Define the Goals → Projects → Tasks → Commitments ownership model and
  migration boundary.
- [x] Add the Decision Journal proposal with rationale, alternatives, evidence,
  status, and provenance rules.
- [x] Implement the smallest shared domain/API slice and expose it through Chat
  and Telegram via the central Tool Registry.
- [x] Add one compact Tasks & Projects surface and project/decision projections
  to Today and Action Center without duplicating task state.

Implementation evidence: migration `032_goals_projects_decisions.sql`,
`backend/app/planning/*`, `backend/app/memory/decision_service.py`,
`/api/planning`, `/api/memory/decisions`, the shared Tool Registry, compact
`/commitments` and `/memory` tabs, and
`backend/tests/test_planning_and_decisions.py`.

Next cycle: improve projections into Today/Action Center and add approval-gated
derived proposals only when a concrete personal workflow requires them.

## Completed Foundation Cycle

The previous foundation cycle is complete. The checked items below are retained as a
traceable delivery record; they are not active work. When a new cycle is opened, promote
at most four unchecked ideas from the parking lot and describe the decision in
[DECISION_LOG.md](decisions/DECISION_LOG.md).

- [x] Implement Commitment Tracker lifecycle and approval-backed proposals
- [x] Connect Commitment Tracker to calendar, email and Telegram reminders
- [x] Define and implement the Unified Approval Control Plane record and API contract (v1)
- [x] Add observability foundation: correlation IDs, structured events, health status and latency telemetry
- [x] Replace ad-hoc SQLite schema updates with versioned migrations
- [x] Add the first deterministic Personal State Engine snapshot and Dashboard view
- [x] Persist daily Personal State snapshots and add State of Me history/report
- [x] Add the read-only Action Center API that normalizes commitments, subscriptions, deadlines and approvals
- [x] **Code Sandbox MVP**: add a bounded workspace, Docker runner, agent tools, explicit write confirmation, allowlisted checks, diff/baseline preview, approval-gated repository apply and a web page (see [CODE_SANDBOX.md](design/CODE_SANDBOX.md)).


## Audit findings — 2026-08-03

These items are documented technical/product debt from the full project audit. They are not automatically promoted into the active four-item cycle.

- [x] **Calendar provider parity:** route Assistant, Telegram, Personal State, morning summary, and Telegram reminders through the same configured calendar service used by the web API (implemented 2026-08-03).
- [x] **Calendar recurrence and assistant parity:** expand local recurring events for future ranges and preserve all-day, recurrence, recurrence-until, and reminder fields through Chat/Telegram tool validation (implemented 2026-08-03).
- [x] **Central Tool Registry:** make schema, Pydantic validation, permission level, dispatcher, and audit metadata one source of truth; add a CI drift check (implemented 2026-08-03).
- [x] **Async I/O boundary:** `backend/app/api/utils.py` now provides the shared thread boundary; calendar/mail, document parsing, subscription email scans, State/Action Center aggregation, agent document retrieval and the morning summary no longer run blocking work on the async event loop (implemented 2026-08-03).
- [x] **Temporal read-model contract:** `backend/app/temporal/time_context.py` centralizes timezone/reference-time handling and `overdue / due_today / upcoming / planned` priority classification for Personal State, Action Center, countdowns, morning Telegram summaries and notification delivery (implemented 2026-08-03).
- [x] **Safety/test hygiene:** default pytest discovery is restricted to `backend/tests`, manual live scripts are documented and excluded, credential checks no longer print values, and `.env.example` starts in local dry-run with external scans disabled (implemented 2026-08-03).
- [x] **Confirmation audit hardening:** pending action claims/cancellations atomically enforce source channel plus chat/session identity; Telegram callback action ids are validated with the nonce; replay, wrong-chat, cross-channel, expiry and concurrent-claim paths are covered; failure details and resolution timestamps are persisted (implemented 2026-08-03).
- [x] **Calendar × Commitments conflict detection v1:** read-only deadline/event and event/event conflict projection in Calendar, Today, Action Center, Chat and Telegram (implemented 2026-08-04; see [CONFLICT_DETECTION.md](design/CONFLICT_DETECTION.md)).


---

## Future Ideas / Parking Lot

Near-to-medium-term concrete features not yet scheduled. Long-term phase items belong in [ROADMAP.md](ROADMAP.md).

**Agent and proactivity**
- [x] **Weather and forecast connector**: read-only weather tool with location resolution, current conditions, forecast, units, provider timeouts, source/timestamp and a structured chat card.
- [x] **Internet access MVP**: add read-only `web_search`/`web_fetch` tools with public-network checks, size/time limits, short caching, provenance, untrusted-content wrapping and browser fallback.
- [x] **Web Research price reliability v1**: normalize common RU product queries for Germany, extract EUR price evidence with confidence, and fall back to search snippets when a source returns HTTP 403.
- **Internet access hardening**: add robots-policy coverage, stronger per-session budgets and a broader Lightpanda/Chromium compatibility matrix.
- [x] **Browser runtime PoC**: compare Lightpanda via Docker/CDP with Playwright/Chromium on a local JavaScript fixture; external-site compatibility and fallback policy remain to be validated.
- **Broader host computer control**: extend the implemented diagnostics and allowlisted URL/path opening with approval-gated process, service, file and OS-specific adapters.
- [x] **Code Sandbox MVP**: let the agent draft and validate small text/code files in a Docker container outside the main project without exposing an arbitrary shell.
- [x] **Subscription Tracker MVP**: detect free-trial or renewal dates in unread email, keep approval-gated proposals with provenance, project them into the shared Approval Center, and remind the user before a known paid charge. Provider cancellation remains a manual user action; see [SUBSCRIPTION_TRACKER.md](design/SUBSCRIPTION_TRACKER.md).
- [x] **Personal State Engine v1**: aggregate current commitments, subscriptions, deadlines and finance into a read-only priority snapshot; see `/api/state` and [ROADMAP.md](ROADMAP.md).
- [x] **Action Center v1**: normalize priorities, due dates, reminders and approval-required actions into `/api/actions`; baseline preferences, budgets and Telegram coalescing are implemented, while mobile delivery and richer policy remain future work.
- [x] **Notification Center v1**: add `/notifications` web view over Action Center with attention/all modes, type filters, summary counters and links to source modules; error lifecycle is now implemented separately in the error-reporting feature.
- **Receipt → Expense proposals**: agent detects a purchase receipt in email and proposes adding it to Finance.
- [x] **Calendar Conflict Checking v1**: warn about existing event/event and deadline/event conflicts without changing user data; pre-save blocking remains future.
- [x] **Calendar × Memory integration:** explicit approved preference checks and pre-save confirmation are implemented for Calendar, Chat and Telegram (2026-08-04; see [CONFLICT_DETECTION.md](design/CONFLICT_DETECTION.md)).
- [x] **Smart Scheduling v1:** Chat and Telegram can propose read-only free calendar slots using the configured provider, shared temporal context, and approved Memory preferences (2026-08-04; see [SMART_SCHEDULING.md](design/SMART_SCHEDULING.md)).
- [x] **Task flow v1:** explicit Chat/Telegram task commands use active Commitments and project into Today, Action Center, Telegram reminders, and explicit Calendar links (2026-08-04; see [TASK_FLOW.md](design/TASK_FLOW.md)).
- [x] **Today Overview v2:** unify the `/dashboard` operational view around one cached Personal State snapshot for schedule, tasks, deadlines, attention items and next actions (2026-08-04; see [TODAY_OVERVIEW.md](design/TODAY_OVERVIEW.md)).
- [x] **Action Center v1.1:** add read/unread, snooze, dismiss, task completion and deadline rescheduling from Today and Notification Center without duplicating domain state (2026-08-04; see [ACTION_CENTER.md](design/ACTION_CENTER.md)).
- **Smart Reminders**: reminders based on deadlines extracted from emails and documents.
- **Commitment Center improvements**: richer extraction, rescheduling and notification preferences.

**Agent brain / Waku-inspired ideas**
- [x] **Retrieval Gate v1**: cheap deterministic routing skips irrelevant operational turns, records the decision/reason in `agent_turn` and fails open on gate errors; improve ambiguous semantic cases later.
- [x] **Procedural Memory / Skills v1**: separate skill storage, built-in safe workflows, deterministic trigger selection, draft/approved/disabled lifecycle and Approval Center integration; richer editing remains future work.
- [x] **Evaluation Release Gate v1**: `python dev-tools/release_gate.py` runs backend tests plus frontend lint/build, exits non-zero on regression and appends verdicts to ignored `logs/release_gate.jsonl`; optional LLM quality judging remains future work.
- [x] **Per-turn Agent Trace v1**: `agent_turn` aggregates memory decisions, tool calls, loop iterations, latency, token estimates and final outcome without storing message content.
- [x] **Document Vault + RAG v1**: separate local artifact storage, bounded extraction/chunking, SQLite FTS5 retrieval, document-related chat context, provenance and `/documents` UI; embeddings, OCR, semantic extraction, reranking and comparison remain future work.
- [x] **Selective OSS component reuse**: integrate MarkItDown for bounded document conversion, FullCalendar for Today/Week/Month rendering, and Radix Dialog for shared modal accessibility; Tiptap remains deferred until formatted notes have a storage contract (implemented 2026-08-04; see [`decisions/OSS_INTEGRATIONS.md`](decisions/OSS_INTEGRATIONS.md)).
- [x] **GitHub OSS audit refresh**: compare candidate projects against Mira's domains, local-first boundary and license policy; next candidate is bounded Document Vault OCR, not a full product embed (implemented 2026-08-04; see [`decisions/OSS_AUDIT_2026-08-04.md`](decisions/OSS_AUDIT_2026-08-04.md)).
- [x] **Computer Control v1 + always-on Windows foundation**: allowlisted URL/path opening behind RED confirmation, host capability endpoint, watchdog, healthcheck and Scheduled Task installer; process control, HTTPS/VPN automation and macOS adapter remain future work.

**Selected Product Ideas**

Only the following ideas from the latest ideation pass are retained. They are not
active tasks until a new cycle is explicitly opened. Subscription → Finance
linking is a completed delivery record; the next product candidate will be chosen
after the current reliability cycle.

- [x] **Subscription → Finance linking**: separate approval-gated proposal creates an idempotent recurring Finance template for supported monthly EUR subscriptions; cancellation disables future generation without deleting history (implemented 2026-08-04; see [SUBSCRIPTION_FINANCE_LINK.md](design/SUBSCRIPTION_FINANCE_LINK.md)).
- [ ] **Security backlog reminders**: periodic reminder for non-critical open security debts, with owner, severity and next action.
- [ ] **Focus mode**: one-tap temporary mode layered on Quiet Hours that suppresses everything except RED/urgent notifications.
- [ ] **Archive instead of delete**: soft-delete/archive behavior for facts, subscriptions, commitments and documents, with recovery where possible.
- [x] **Document-to-domain links**: connect a document to a commitment, calendar event or subscription while preserving provenance; implemented in [`docs/design/DOCUMENT_LINKS.md`](design/DOCUMENT_LINKS.md).
- [x] **Document-derived action proposals**: detect high-confidence obligation/date pairs and route task/event choices through Approval Center; implemented in [`docs/design/DOCUMENT_PROPOSALS.md`](design/DOCUMENT_PROPOSALS.md).
- [ ] **OCR for scanned documents**: extract searchable text from photos and scanned PDFs.
- [ ] **Document comparison**: compare two versions of a document and explain meaningful changes in plain language.
- [ ] **Unverified external data area**: clearly separate web prices, news and other external results from trusted local facts, with source, retrieval date and freshness.
- [ ] **Evidence bundle persistence**: normalize bounded source references for document, memory, email and web-derived answers/proposals without creating a new domain.
- [x] **Unified Notification Center v1**: one Action Center projection for approvals, reminders, errors, subscription warnings and agent proposals; v1.1 adds read/unread, snooze, dismiss and Commitment actions.
- [x] **Mobile four-action mode**: optimize the phone experience around Chat, Tasks, Notifications and File Upload; place the remaining sections under “More” (implemented 2026-08-04).
- [ ] **Monthly security report**: summarize open security findings, active permissions, failed checks and stale configuration.
- [ ] **Temporary-file cleanup**: automatically clean sandbox artifacts, transient logs and expired upload/cache files according to safe retention rules.
- [x] **Error reporting with lifecycle**: save error reports inside the project with correlation ID and context; track `new → fixing → fixed → verified → closed` and preserve the fix reference and verification result.

**Notifications**
- [x] **Quiet hours configuration**: suppress non-urgent Telegram notifications during user-defined hours.
- [x] **Notification budget / coalescing**: rate-limit low-priority alerts and batch Action Center items instead of sending individually.
- [x] **Notification preferences UI**: configure delivery, timezone, quiet hours, minimum priority, budgets and coalescing from `/notifications/preferences`.

**Mail**
- **Auto-file rules (approval-based)**: user-configured rules to categorize/move emails, requiring approval before activation.
- **Threading**: group emails into conversation threads.
- **Unread badge in navigation**: show unread count in sidebar.

**Frontend**
- **Voice Input UI (web microphone)**: microphone button in web chat using local whisper.cpp (Telegram voice pipeline already exists).
- **Calendar Deadlines tab improvements**: interactive reminders with natural language (e.g. "3 days left — ready or reschedule?").
- **Dashboard drag-and-drop widgets**: Gridstack-based resize and reorder.

**Infrastructure**
- **Read-only host diagnostics**: CPU, RAM, disk and top-process metrics are now available through the system API and Dashboard; process control remains explicitly deferred.
- **Always-on server**: evaluate Raspberry Pi or mini-PC to replace MacBook Air as permanent host.
- **GitHub Integration**: include open issues/PRs in morning summary.
- [x] **Finance: source_template_id dedup**: transactions retain `source_template_id` and recurring processing deduplicates within the template period (implemented 2026-08-04; see [FINANCE_MODEL.md](design/FINANCE_MODEL.md)).
- [x] **Finance Assistant parity**: web Chat and Telegram share forecast, one-off transaction, and recurring-template tools through the central registry (implemented 2026-08-04; see [FINANCE_ASSISTANT.md](design/FINANCE_ASSISTANT.md)).
- [x] **Finance → Action Center projection**: surface the next active recurring Finance occurrence in Today, Notification Center and the shared Telegram delivery path without duplicating linked subscription signals (implemented 2026-08-04; see [ACTION_CENTER.md](design/ACTION_CENTER.md)).

**Accessibility and code quality**
- **Frontend A11y**: ARIA labels, tab index, and keyboard navigation across all components.
- **Frontend data-fetching DRY**: consolidate fetch/loading/error hooks across graph, review, and consolidation pages.
- **Backend type annotations**: add type hints to `caldav_connector.py`, `mail_connector.py`, `main.py`, `db.py` return types.
