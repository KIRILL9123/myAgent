# Architecture Status Snapshot (2026-07-31)

This document reflects the **current code reality**.

## Implemented
- FastAPI backend bootstrap, scheduler, API-key middleware: `backend/app/main.py`
- Orchestrator tool loop with permission gating and RED confirmation: `backend/app/agent/orchestrator.py`
- Dry-run / side-effect isolation: `backend/app/core/execution_mode.py` + guarded in connectors
- Pydantic tool-call validation: `backend/app/agent/tool_models.py` + integrated in `execute_tool()`
- SQLite backup/restore with daily cron + retention: `backend/app/storage/backup.py`
- Temporal fact validity (provenance, valid_from/valid_to, expired filter): `backend/app/storage/db.py` migrations + `backend/app/memory/memory_service.py`
- Connectors and integrations:
  - CalDAV: `backend/app/connectors/caldav_connector.py`
  - Mail (IMAP/SMTP): `backend/app/connectors/mail_connector.py`
  - Telegram listener/notifier: `backend/app/notifications/telegram_listener.py`, `backend/app/notifications/telegram_notifier.py`
- Memory Layer (SQLite + approval + graph + relation building): `backend/app/memory/*`
- Finance and countdown domains: `backend/app/finance/*`, `backend/app/countdown/*`
- React + Vite + TypeScript frontend dashboard: `frontend/src/*`
- Controlled web access (`web_search`, `web_fetch`) with prompt-injection guard (`sanitize_tool_result`, `<untrusted_external_content>` wrapping) and web source cards: `backend/app/connectors/web_connector.py`, `backend/app/agent/orchestrator.py` — covered by `backend/tests/test_web_connector.py`
- Weather cards (read-only forecast lookups for chat): `backend/app/connectors/weather_connector.py` — covered by `backend/tests/test_weather_connector.py`
- Host diagnostics / observability (correlation IDs, structured event log, system status, host diagnostics): `backend/app/observability/*` — covered by `backend/tests/test_observability.py`, `backend/tests/test_host_diagnostics.py`
- Unified approval center (projection of memory facts, commitment proposals and RED actions into one approval record + API + web center): `backend/app/approvals/approval_service.py`, `backend/app/api/approvals.py`, `frontend/src/pages/ApprovalsPage.tsx` — covered by `backend/tests/test_approvals.py`
- Commitment tracker (proposal lifecycle PROPOSED→ACTIVE→COMPLETED/CANCELLED, calendar links, email extraction, reminders): `backend/app/commitments/*` — covered by `backend/tests/test_commitments.py`

## Partially implemented / inconsistent
- ~~API auth bypass check referenced `/api/health`, but route is `/health`~~ — **fixed** (`backend/app/main.py`)
- ~~Scheduled summary parses connector outputs as JSON strings, while connectors return Python objects~~ — **fixed** (`backend/app/agent/scheduled_tasks.py`)
- ~~Mail error contract is inconsistent (`{"error": ...}` vs `{"status":"error"}`)~~ — **fixed** (`backend/app/connectors/mail_connector.py`)
- Countdown tools (`add_countdown`, `get_all_countdowns`) were missing from `tool_permissions.json` — **fixed**

## Planned / not implemented yet
- Commitment Tracker: deep event history and approval-policy unification (single approval record today is a projection; unified per-domain policy remains future work)
- Nightly "State of Me" brief; quiet hours and notification budget (see `docs/MASTER_VISION_ALIGNMENT.md`)

## Obsolete or stale references
- `docs/ARCHITECTURE.md` is up to date (Mem0 removed, React+Vite+TypeScript stack accurately described, historical note removed)
- `frontend/README.md` has been replaced with a project-specific frontend README

## High-risk operational areas
- External side effects (SMTP/CalDAV/Telegram) are reachable from app runtime and some dev scripts
- Dev scripts in `dev-tools/` can call real external services if credentials are present
