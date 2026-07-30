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


---

## Future Ideas / Parking Lot

Near-to-medium-term concrete features not yet scheduled. Long-term phase items belong in [ROADMAP.md](ROADMAP.md).

**Agent and proactivity**
- [x] **Weather and forecast connector**: read-only weather tool with location resolution, current conditions, forecast, units, provider timeouts, source/timestamp and a structured chat card.
- [x] **Internet access MVP**: add read-only `web_search`/`web_fetch` tools with public-network checks, size/time limits, short caching, provenance, untrusted-content wrapping and browser fallback.
- **Internet access hardening**: add robots-policy coverage, stronger per-session budgets and a broader Lightpanda/Chromium compatibility matrix.
- [x] **Browser runtime PoC**: compare Lightpanda via Docker/CDP with Playwright/Chromium on a local JavaScript fixture; external-site compatibility and fallback policy remain to be validated.
- **Host computer control**: design an approval-gated, sandboxed capability for diagnostics and selected actions on the host OS, with separate Windows and macOS adapters.
- **Trial subscription cancellation reminders**: detect free-trial or renewal dates and remind the user before a paid charge, with an explicit cancellation checklist.
- **Receipt → Expense proposals**: agent detects a purchase receipt in email and proposes adding it to Finance.
- **Calendar Conflict Checking**: warn before creating/modifying an event that overlaps with an existing one.
- **Calendar × Memory integration**: warn when a new event conflicts with approved user preferences (e.g. "no meetings before 10:00").
- **Smart Reminders**: reminders based on deadlines extracted from emails and documents.
- **Commitment Center improvements**: richer extraction, rescheduling and notification preferences.

**Notifications**
- **Quiet hours configuration**: suppress non-urgent Telegram notifications during user-defined hours.
- **Notification budget / coalescing**: rate-limit low-priority alerts; batch instead of sending individually.

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
