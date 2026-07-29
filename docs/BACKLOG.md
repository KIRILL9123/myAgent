# Backlog

> **Responsibility**: Active work cycle (max 4 items) + future parking lot.  
> The complete long-term vision and phased roadmap belongs in [ROADMAP.md](ROADMAP.md).

---

## Active Next Cycle

Maximum 4 tasks. These are the only items actively worked on in the current cycle. Everything else lives in the parking lot below.

_Cycle complete — awaiting next selection._


---

## Future Ideas / Parking Lot

Near-to-medium-term concrete features not yet scheduled. Long-term phase items belong in [ROADMAP.md](ROADMAP.md).

**Agent and proactivity**
- **Receipt → Expense proposals**: agent detects a purchase receipt in email and proposes adding it to Finance.
- **Calendar Conflict Checking**: warn before creating/modifying an event that overlaps with an existing one.
- **Calendar × Memory integration**: warn when a new event conflicts with approved user preferences (e.g. "no meetings before 10:00").
- **Smart Reminders**: reminders based on deadlines extracted from emails and documents.
- **Commitment Tracker**: full domain per [domain/COMMITMENT_CONTRACT.md](domain/COMMITMENT_CONTRACT.md) (planned Phase 2).

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
- **Always-on server**: evaluate Raspberry Pi or mini-PC to replace MacBook Air as permanent host.
- **GitHub Integration**: include open issues/PRs in morning summary.
- **Finance: source_template_id dedup**: add `source_template_id` to transactions table to fix the known duplicate-template edge case.

**Accessibility and code quality**
- **Frontend A11y**: ARIA labels, tab index, and keyboard navigation across all components.
- **Frontend data-fetching DRY**: consolidate fetch/loading/error hooks across graph, review, and consolidation pages.
- **Backend type annotations**: add type hints to `caldav_connector.py`, `mail_connector.py`, `main.py`, `db.py` return types.
