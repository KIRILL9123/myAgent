# Dry-Run / Side-Effect Simulation Architecture

## Why this is required
A prior regression executed a real-world side effect. The system must prevent this by construction, not by convention.

## Current side-effect paths
- SMTP send: `backend/app/connectors/mail_connector.py` (`send_email`)
- IMAP read (network + local sync-state mutation): `backend/app/connectors/mail_connector.py`
- CalDAV create/modify/delete: `backend/app/connectors/caldav_connector.py`
- Telegram send/polling: `backend/app/notifications/telegram_notifier.py`, `backend/app/notifications/telegram_listener.py`
- Finance DB mutations: `backend/app/finance/finance_service.py`
- Scheduler-triggered effects: `backend/app/agent/scheduled_tasks.py`, `backend/app/main.py`

## Dangerous paths today
- `dev-tools/test_*` scripts can call real services when credentials are present.
- App startup launches Telegram polling task automatically.
- Read operations can still mutate state (`mail_sync_state` updates in unread-mail flow).

## Proposed architecture boundaries
1. **Execution policy object** (`ExecutionMode = DRY_RUN | REAL`) injected at app edges (API, orchestrator, scheduler).
2. **Connector boundary**: all networked connectors require policy and return structured intent in dry-run.
3. **Mutation boundary**: service-level write functions require policy; dry-run path returns `{"status":"dry_run","would_do":...}`.
4. **Scheduler boundary**: scheduler jobs run dry-run in CI/sandbox unless explicitly enabled.

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
