# Backlog

> **Responsibility**: Active work cycle (max 4 items) + future parking lot.  
> The complete long-term vision and phased roadmap belongs in [ROADMAP.md](ROADMAP.md).

---

## Active Next Cycle

Maximum 4 tasks. These are the only items actively worked on in the current cycle. Everything else lives in the parking lot below.

The current cycle is intentionally focused on the missing product foundations identified
in [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md):

- [x] Implement Commitment Tracker lifecycle and approval-backed proposals
- [x] Connect Commitment Tracker to calendar, email and Telegram reminders
- [x] Define and implement the Unified Approval Control Plane record and API contract (v1)
- [x] Add observability foundation: correlation IDs, structured events, health status and latency telemetry
- [x] Replace ad-hoc SQLite schema updates with versioned migrations
- [x] Add the first deterministic Personal State Engine snapshot and Dashboard view
- [x] Persist daily Personal State snapshots and add State of Me history/report
- [x] Add the read-only Action Center API that normalizes commitments, subscriptions, deadlines and approvals
- [x] **Code Sandbox MVP**: add a bounded workspace, Docker runner, agent tools, explicit write confirmation, allowlisted checks, diff/baseline preview, approval-gated repository apply and a web page (see [CODE_SANDBOX.md](design/CODE_SANDBOX.md)).


---

## Future Ideas / Parking Lot

Near-to-medium-term concrete features not yet scheduled. Long-term phase items belong in [ROADMAP.md](ROADMAP.md).

**Agent and proactivity**
- [x] **Weather and forecast connector**: read-only weather tool with location resolution, current conditions, forecast, units, provider timeouts, source/timestamp and a structured chat card.
- [x] **Internet access MVP**: add read-only `web_search`/`web_fetch` tools with public-network checks, size/time limits, short caching, provenance, untrusted-content wrapping and browser fallback.
- [x] **Web Research price reliability v1**: normalize common RU product queries for Germany, extract EUR price evidence with confidence, and fall back to search snippets when a source returns HTTP 403.
- **Internet access hardening**: add robots-policy coverage, stronger per-session budgets and a broader Lightpanda/Chromium compatibility matrix.
- [x] **Browser runtime PoC**: compare Lightpanda via Docker/CDP with Playwright/Chromium on a local JavaScript fixture; external-site compatibility and fallback policy remain to be validated.
- **Host computer control**: design an approval-gated, sandboxed capability for diagnostics and selected actions on the host OS, with separate Windows and macOS adapters.
- [x] **Code Sandbox MVP**: let the agent draft and validate small text/code files in a Docker container outside the main project without exposing an arbitrary shell.
- [x] **Subscription Tracker MVP**: detect free-trial or renewal dates in unread email, keep approval-gated proposals with provenance, project them into the shared Approval Center, and remind the user before a known paid charge. Provider cancellation remains a manual user action; see [SUBSCRIPTION_TRACKER.md](design/SUBSCRIPTION_TRACKER.md).
- [x] **Personal State Engine v1**: aggregate current commitments, subscriptions, deadlines and finance into a read-only priority snapshot; see `/api/state` and [ROADMAP.md](ROADMAP.md).
- [x] **Action Center v1**: normalize priorities, due dates, reminders and approval-required actions into `/api/actions`; delivery preferences and Telegram coalescing remain future work.
- **Receipt → Expense proposals**: agent detects a purchase receipt in email and proposes adding it to Finance.
- **Calendar Conflict Checking**: warn before creating/modifying an event that overlaps with an existing one.
- **Calendar × Memory integration**: warn when a new event conflicts with approved user preferences (e.g. "no meetings before 10:00").
- **Smart Reminders**: reminders based on deadlines extracted from emails and documents.
- **Commitment Center improvements**: richer extraction, rescheduling and notification preferences.

**Agent brain / Waku-inspired ideas**
- [x] **Retrieval Gate v1**: cheap deterministic routing skips irrelevant operational turns, records the decision/reason in `agent_turn` and fails open on gate errors; improve ambiguous semantic cases later.
- [x] **Procedural Memory / Skills v1**: separate skill storage, built-in safe workflows, deterministic trigger selection, draft/approved/disabled lifecycle and Approval Center integration; richer editing remains future work.
- [x] **Evaluation Release Gate v1**: `python dev-tools/release_gate.py` runs backend tests plus frontend lint/build, exits non-zero on regression and appends verdicts to ignored `logs/release_gate.jsonl`; optional LLM quality judging remains future work.
- [x] **Per-turn Agent Trace v1**: `agent_turn` aggregates memory decisions, tool calls, loop iterations, latency, token estimates and final outcome without storing message content.

**Notifications**
- [x] **Quiet hours configuration**: suppress non-urgent Telegram notifications during user-defined hours.
- [x] **Notification budget / coalescing**: rate-limit low-priority alerts and batch Action Center items instead of sending individually.

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
- **Finance: source_template_id dedup**: add `source_template_id` to transactions table to fix the known duplicate-template edge case.

**Accessibility and code quality**
- **Frontend A11y**: ARIA labels, tab index, and keyboard navigation across all components.
- **Frontend data-fetching DRY**: consolidate fetch/loading/error hooks across graph, review, and consolidation pages.
- **Backend type annotations**: add type hints to `caldav_connector.py`, `mail_connector.py`, `main.py`, `db.py` return types.
