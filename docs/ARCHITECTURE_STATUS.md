# Architecture Status Snapshot (2026-07-27)

This document reflects the **current code reality**.

## Implemented
- FastAPI backend bootstrap, scheduler, API-key middleware: `backend/app/main.py`
- Orchestrator tool loop with permission gating and RED confirmation: `backend/app/agent/orchestrator.py`
- Connectors and integrations:
  - CalDAV: `backend/app/connectors/caldav_connector.py`
  - Mail (IMAP/SMTP): `backend/app/connectors/mail_connector.py`
  - Telegram listener/notifier: `backend/app/notifications/telegram_listener.py`, `backend/app/notifications/telegram_notifier.py`
- Memory Layer (SQLite + approval + graph + relation building): `backend/app/memory/*`
- Finance and countdown domains: `backend/app/finance/*`, `backend/app/countdown/*`
- React + Vite + TypeScript frontend dashboard: `frontend/src/*`

## Partially implemented / inconsistent
- ~~API auth bypass check referenced `/api/health`, but route is `/health`~~ — **fixed** (`backend/app/main.py`)
- Scheduled summary parses connector outputs as JSON strings, while connectors return Python objects: `backend/app/agent/scheduled_tasks.py`
- Mail error contract is inconsistent (`{"error": ...}` vs `{"status":"error"}`): `backend/app/connectors/mail_connector.py`, `backend/app/api/utils.py`

## Planned / not implemented yet
- Dry-run architecture (global side-effect simulation boundary)
- Commitment Tracker domain implementation
- Pydantic tool-call validation layer before dispatch
- SQLite backup/restore operational flow

## Obsolete or stale references
- `docs/ARCHITECTURE.md` is up to date (Mem0 removed, React+Vite+TypeScript stack accurately described, historical note removed)
- `frontend/README.md` has been replaced with a project-specific frontend README

## High-risk operational areas
- External side effects (SMTP/CalDAV/Telegram) are reachable from app runtime and some dev scripts
- Dev scripts in `dev-tools/` can call real external services if credentials are present
