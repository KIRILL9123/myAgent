# Backlog

This document tracks future ideas and modules that are not yet scheduled for a specific phase, but are recorded here so they aren't forgotten.

## Active Next Cycle

Max 4 tasks. These are the only items actively worked on in the current cycle. Everything else lives under Future Ideas / Parking Lot below.

1. **Dry-Run / Side-Effect Isolation** — make it impossible by construction for tests/agents to trigger a real email/calendar/Telegram/finance side effect (see `docs/DRY_RUN_ARCHITECTURE.md`).
2. **Pydantic Tool Validation** — unify and validate tool inputs before execution (see `docs/TOOL_VALIDATION_PLAN.md`).
3. **SQLite Backup & Restore** — data protection before any schema-heavy domain expansion (see `docs/BACKUP_RESTORE_PLAN.md`).
4. **Fact Confidence / Temporal Memory** — prepare the Memory Layer with confidence/provenance/temporal metadata (see `docs/MEMORY_EVOLUTION.md`).

## Future Ideas / Parking Lot
- **Voice Input UI (Web Chat microphone control)**: currently not implemented in frontend (Telegram voice pipeline exists).
- **Calendar Conflict Checking**: Proactively check for calendar conflicts when creating events.
- **Smart Reminders**: Reminders based on dates/deadlines extracted from emails.
- **Long-term Memory**: ~~Store persistent facts about the user, rather than just the dialogue history.~~ *(Implemented via custom Memory Layer; Mem0 removed)*
- **GitHub Integration**: Include a summary of open issues/PRs in the morning summary.
- **Autonomous Email Categorization**: Automatically categorize incoming emails (Important/Spam/Wait).
- **Always-on Server**: Investigate whether a separate always-on server (Raspberry Pi/mini PC) is needed since a MacBook Air cannot act as a permanent host.
