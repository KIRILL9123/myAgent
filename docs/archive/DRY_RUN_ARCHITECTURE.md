# Dry-Run / Side-Effect Simulation Architecture

## Why this is required
A prior regression executed a real-world side effect. The system must prevent this by construction, not by convention.

## Current side-effect paths (all guarded as of Cycle 1)

### External side effects (network)
- SMTP send: `backend/app/connectors/mail_connector.py` (`send_email`) — **guarded**
- CalDAV create/modify/delete: `backend/app/connectors/caldav_connector.py` — **guarded**
- Telegram send: `backend/app/notifications/telegram_notifier.py` (`send_notification`) — **guarded**
- Telegram polling: `backend/app/notifications/telegram_listener.py` — **skipped in dry_run at startup** (main.py)
- IMAP read (network): `backend/app/connectors/mail_connector.py` — read is safe, but sync-state mutation now **guarded**

### Local persistent writes (SQLite)
- Finance: `add_transaction`, `delete_transaction` — **guarded**
- Countdown: `add_countdown`, `delete_countdown` — **guarded** (Cycle 1)
- Memory: `save_pending_fact`, `approve_fact`, `reject_fact`, `consolidate_facts`, `save_relation`, `update_fact_timestamp`, `save_approved_fact`, `mark_facts_as_merged` — **all guarded** (Cycle 1)
- Email sync state: `update_last_seen_uid` in `list_unread_emails` — **guarded** (Cycle 1)
- Recurring templates: `add_recurring_template`, `delete_recurring_template` — **guarded** (Cycle 1)
- Recurring transaction processing: `process_recurring_transactions` — **guarded** (Cycle 1)

### Background / scheduler
- Morning summary: Telegram notification guarded; CalDAV/IMAP reads are safe; sync-state now uses `bypass_last_seen` in dry_run (Cycle 1)
- Nightly consolidation: uses `find_consolidation_candidates` (read-only); writes guarded
- Recurring transactions: scheduler job **guarded** (Cycle 1)

## Safety invariant (Cycle 1)

**In DRY_RUN mode:**
- No external network side effects (email, calendar mutations, Telegram messages)
- No persistent SQLite state mutation (facts, transactions, countdowns, templates, sync state)
- No Telegram polling (listener disabled at startup)
- Scheduler reads are allowed; writes are suppressed
- All guarded functions return `{"status": "dry_run", "would_do": {...}}` or sentinel values

**Developer tools (dev-tools/):**
- Scripts that cause side effects require `EXECUTION_MODE=real` and abort with an error otherwise
- Read-only scripts are explicitly documented as safe

## Required test doubles/fakes
- `FakeMailConnector` (captures outgoing email payloads)
- `FakeCalendarConnector` (captures create/modify/delete intents)
- `FakeTelegramNotifier` (captures outbound notification payloads)
- `FakeFinanceWriter` (captures intended inserts/deletes)

## Credential safety strategy
- Tests/CI must set `EXECUTION_MODE=DRY_RUN` and reject startup if mode is REAL.
- Tests must fail if production credential vars are present (allowlist-based env guard).
- Real connector constructors must be blocked in dry-run mode.

## CI and agent sandbox behavior
- Default execution mode: DRY_RUN.
- No network side effects allowed.
- Scheduler and polling workers disabled unless explicit, isolated integration job.

## How to verify intended actions without execution
- Return and assert intent payloads:
  - tool name
  - normalized arguments
  - target account/calendar/resource
  - timestamp/session_id
- Persist intent audit records separate from execution records.

## Migration order (planning)
1. Introduce execution-mode config and policy propagation.
2. Add dry-run return contracts to side-effecting tools.
3. Add env guards for test/CI.
4. Add regression tests asserting `would_do` outputs and zero real I/O.
