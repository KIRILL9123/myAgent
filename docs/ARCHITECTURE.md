# Architecture

> Runtime guidance lives in [OPERATIONS.md](OPERATIONS.md). Product placement and domain ownership live in [PRODUCT_ARCHITECTURE.md](../PRODUCT_ARCHITECTURE.md). Feature coverage is tracked in [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md). The former status snapshot is preserved in `docs/archive/`.

## Overview

Mira is structured with a FastAPI backend driving an orchestration loop, connecting to local LLMs (Ollama) and external services (CalDAV, IMAP, and eventually Home Assistant).

## Data Flow

1. **Input**: User sends a request via `/chat` endpoint (REST/WebSocket) or via Telegram Bot message.
2. **Listener**: `telegram_listener.py` intercepts Telegram messages using long-polling, validating `TELEGRAM_CHAT_ID` before routing.
3. **Orchestrator**: The central agent loop receives the request and builds a system prompt containing the available tools and conversation history.
4. **LLM**: The system prompt and user input are sent to the configured LLM provider (Ollama or OpenAI-compatible Bonsai) via `llm.py`.
5. **Tool Selection**: The LLM decides if a tool call is needed and returns a structured response.
6. **Permission Check**: The orchestrator intercepts the tool call and passes it to `permission_checker.py`.
    - **Green/Yellow**: Execution proceeds immediately.
    - **Red**: The action is stored as pending and the user is asked for explicit confirmation.
- **Execution**: The tool uses the owning domain service (for example, `calendar_service.py`) before reaching a connector such as `caldav_connector.py` or `mail_connector.py`.
7. **Audit**: The action is logged to `audit_log.py`, including PENDING_CONFIRMATION → CONFIRMED/CANCELLED for red actions.
8. **Response**: The result is fed back to the LLM to formulate the final answer to the user.
## Audit findings and follow-up

The following gaps were confirmed in the read-only project audit on 2026-08-03. The calendar, tool-governance, runtime, and confirmation items were fixed in the same implementation cycle; the remaining items are still open:

- **Calendar provider parity (fixed 2026-08-03):** `calendar_service.py` now resolves local SQLite or CalDAV for the web API, Assistant, Personal State, scheduled summaries, and notification delivery.
- **Local recurrence (fixed 2026-08-03):** local daily, weekly, monthly, and yearly events expand into requested future ranges with recurrence end dates and reminder metadata preserved.
- **Assistant calendar contract (fixed 2026-08-03):** all-day, recurrence, recurrence end, and reminder fields now survive tool validation and dispatch for Chat and Telegram.
- **Tool governance drift (fixed 2026-08-03):** `tool_registry.py` now owns the LLM schema, Pydantic model, permission, handler and audit metadata; `dev-tools/check_tool_registry.py` fails when those layers drift.
- **Blocking external I/O (fixed 2026-08-03):** `run_blocking()` / `run_api_tool()` now isolate CalDAV, IMAP, document ingestion/search, subscription email scans, State/Action Center aggregation and scheduled morning-summary reads from the event loop. Agent document retrieval uses the same thread boundary.
- **Temporal read-model contract (fixed 2026-08-03):** `temporal/time_context.py` supplies one injected reference instant, user timezone and shared due-state classification to Personal State, Action Center, countdowns, morning Telegram summaries and notification delivery. Stored timestamps are compared in UTC; calendar-day semantics use the configured notification timezone.
- **Confirmation audit and channel identity (fixed 2026-08-03):** pending action claims and cancellations now atomically bind the nonce to the source channel, chat/session identity, and (for Telegram) the callback action id. Replay, cross-channel, wrong-chat, expiry, and concurrent-claim paths are covered by regression tests; execution failure details are persisted with resolution timestamps.
- **Safety/test hygiene (fixed 2026-08-03):** a fresh `.env.example` uses local dry-run defaults, pytest discovery is confined to backend tests, manual live integration scripts are documented separately, and credential diagnostics report presence without exposing values.
- **Calendar × Commitments conflict detection (fixed 2026-08-04):** the read-only conflict projection detects event/deadline and event/event overlaps and exposes the same result to Calendar, Today, Action Center, Chat and Telegram without creating a duplicate conflict entity.
- **Smart Scheduling (fixed 2026-08-04):** the shared `find_calendar_slots` GREEN tool proposes read-only free slots through Chat and Telegram using the configured Calendar provider, `TemporalContext`, and approved Memory scheduling preferences; `create_event` remains the explicit write path after user selection.
- **Task flow (fixed 2026-08-04):** `create_task`, `list_tasks`, `reschedule_task`, `complete_task`, and `cancel_task` use the existing Commitment service for Chat and Telegram; Today, Action Center, Telegram reminders, and explicit Calendar links consume the same record without introducing a tasks table.
- **Today Overview (fixed 2026-08-04):** `/dashboard` renders one cached `GET /api/state/` snapshot through `TodayOverviewWidget`; the projection combines schedule, active commitments, deadlines, attention items, and next actions without creating duplicate domain records or parallel dashboard fetches.
- **Action Center v1.1 (fixed 2026-08-04):** `action_states` stores only read/snooze/dismiss projection metadata; `/api/actions/{id}` controls never replace domain status, while Commitment completion and rescheduling call the existing Commitment service.
- **Mobile four-action mode (fixed 2026-08-04):** the responsive shell keeps Chat, Tasks, Notifications and document Upload available in one touch-friendly bar; secondary routes remain in the expandable menu and upload reuses `/api/documents/upload`.
- **Document-to-domain links (fixed 2026-08-04):** Document Vault now stores explicit, idempotent relations to existing commitments, calendar events, and subscriptions; the card UI resolves current picker targets without creating a second lifecycle or top-level route. The contract is documented in [`design/DOCUMENT_LINKS.md`](design/DOCUMENT_LINKS.md).
- **Document-derived action proposals (fixed 2026-08-04):** high-precision obligation/date candidates flow through the existing `DOCUMENT_PROPOSAL` approval kind; only approval creates an existing Commitment or Calendar event, then a derived document link preserves provenance. Chat and Telegram use the same `scan_document_proposals` and `propose_document_action` registry tools.
- **Selective OSS reuse (fixed 2026-08-04):** Document Vault extraction uses the local-bytes-only MarkItDown adapter, Calendar uses the standard FullCalendar React renderer, and the shared Dialog uses Radix modal primitives. Domain services, FTS5, approval/conflict boundaries and existing design tokens remain Mira-owned; the decision record is in [`decisions/OSS_INTEGRATIONS.md`](decisions/OSS_INTEGRATIONS.md).
- **Subscription → Finance boundary (fixed 2026-08-04):** activating a subscription may create a separate `SUBSCRIPTION_FINANCE_LINK` proposal. Only that second approval creates a recurring template; cancellation deactivates future generation while preserving ledger history. The contract is in [`design/SUBSCRIPTION_FINANCE_LINK.md`](design/SUBSCRIPTION_FINANCE_LINK.md).

These findings are tracked in [BACKLOG.md](BACKLOG.md), with safety implications mirrored in [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md).

## Frontend Modules

The frontend is structured as a compact React + TypeScript + Vite workspace. Product domains and route placement are governed by [PRODUCT_ARCHITECTURE.md](../PRODUCT_ARCHITECTURE.md).
- **Today**: A projection of current state and next actions, not a second source of truth.
- **Assistant**: Chat and Telegram entry points backed by the shared orchestrator.
- **Calendar**: Events and related deadline views.
- **Tasks & Projects**: Commitments today; project and task hierarchy remains planned.
- **Finance**: Transactions, recurring templates, and subscription context.
- **Knowledge**: Memory facts, notes, skills, and document artifacts.
- **Communication**: Mail and external message inputs.
- **Action Center**: A cross-domain read model for attention, approvals, reminders, and errors.

## Layers

- **API Layer**: `fastapi` entrypoints for client communication.
- **Agent Layer**: Core intelligence, tool calling loops, session-based memory for confirmations.
  - **Memory Sublayer**: custom SQLite-backed Memory Layer (`backend/app/memory/*`) with human approval flow, relation graphing, and consolidation support.
- **Permission Layer**: Hardcoded, strictly enforced security boundaries declared in `backend/app/agent/tool_registry.py`.
- **Voice Sublayer**: `transcriber.py` uses `openai-whisper` for local speech-to-text recognition.
- **Connector Layer**: Adapters for third-party services:
  - `caldav_connector.py` — iCloud Calendar (read + write)
  - `mail_connector.py` — IMAP (read) and SMTP (write) for multiple accounts (Gmail, Ukrnet)
- **Background Layer**: 
  - `scheduled_tasks.py` — APScheduler cron jobs for proactive tasks (e.g. morning summary)
  - `telegram_notifier.py` — Push notifications to Telegram
