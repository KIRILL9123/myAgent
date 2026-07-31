# Operations and Reliability

This is the canonical operational guide. Detailed historical plans remain in
`docs/archive/` and are retained as design history.

## Runtime components

- FastAPI backend on port 8000.
- React/Vite dashboard served from `frontend/dist`.
- Bonsai OpenAI-compatible model server on `127.0.0.1:8080`.
- SQLite as the authoritative structured-state store.
- APScheduler for scheduled jobs and Telegram polling for notifications.

Subscription Tracker runs a daily read-only scan of unread IMAP messages at 04:30
and checks approved subscription reminders every 15 minutes. Disable the mailbox
scan with `SUBSCRIPTION_EMAIL_SCAN_ENABLED=false`; configure accounts and the
reminder lead time with `SUBSCRIPTION_EMAIL_SCAN_ACCOUNTS` and
`SUBSCRIPTION_REMINDER_LEAD_DAYS`. The scan never marks messages read and never
cancels a provider subscription.

Personal State is computed on demand from the authoritative domain tables. The
Dashboard uses the local-only snapshot for fast loading; `/state` and `/api/state`
may additionally read the configured calendar and mail connectors. Connector
failures are reported per domain and do not invalidate local commitments,
subscriptions, deadlines or finance signals.
Daily persistent snapshots are refreshed by APScheduler at 08:10 and stored in
the `state_snapshots` table. Re-running the job on the same day updates that day
instead of creating duplicate history entries.

## Startup and health checks

1. Start the Bonsai model server.
2. Start the FastAPI backend.
3. Verify `GET /health`.
4. Verify Bonsai `GET /v1/models`.
5. Run the live smoke test when validating a deployment:
   `RUN_E2E=1 pytest backend/tests/test_e2e_smoke.py -q`.

Startup reconciliation is planned: after downtime the service should identify missed
jobs, stale mail/finance state, pending approvals and summaries that need recovery rather
than relying only on APScheduler misfire handling.

## Testing

- Unit and API suite: `pytest backend/tests -q`.
- Deterministic release gate: `python dev-tools/release_gate.py` (use `--backend-only` or
  `--frontend-only` for focused checks). It runs backend tests and frontend lint/build,
  returns a failing exit code on regression and appends a compact verdict to
  `logs/release_gate.jsonl`.
- Live E2E suite is opt-in because it contacts local running services.
- Every production-relevant regression becomes a permanent test.
- External side effects are prohibited in CI and sandbox runs.

## Backups and recovery

- SQLite backups run through the backup service with retention.
- Restore procedure: stop the backend, restore a verified backup to the configured
  database path, run integrity checks and migrations, then restart and verify health.
- Future backups must cover configuration, document artifacts and a secrets/key strategy.
- Encrypted, versioned exports are planned in addition to SQLite snapshots.

## Database migrations

The current code contains compatibility checks for legacy SQLite schemas. The next
reliability step is a numbered migration system or Alembic so schema history, ordering,
rollback expectations and deployment state are explicit.

## Observability target

Operational records should distinguish normal logs from durable events. The target set is:

- correlation/request ID;
- structured logs;
- model calls and token usage;
- tool traces and permission outcomes;
- latency and error metrics;
- scheduler/job events;
- notification and approval events.

The Dashboard now exposes the live backend/model status and the API exposes telemetry
summary and recent events. Request count, failures, RED actions, tool calls, average
latency and one content-free `agent_turn` aggregate per orchestrator turn are stored in
the `observability_events` table and can be queried through `/api/system/telemetry` and
`/api/system/events`. The aggregate includes Retrieval Gate decision/reason, loop
iterations, memory hit/miss, token estimates and final outcome without persisting user
message content. The v1 gate is deterministic and skips clearly operational requests;
if its code fails, the orchestrator retrieves memory as a safe fallback.

Procedural skills are stored separately from factual memory in `procedural_skills`.
Built-in safety workflows are approved by default; user-created skills start as `draft`,
appear in the Approval Center as `SKILL`, and become selectable only after approval.
The runtime selects skills by deterministic trigger overlap and treats their steps as
workflow guidance, never as a way to bypass permissions or confirmations.

## Request budgets

Each agent request should have maximum time, LLM calls, tool calls and tokens. When a
budget is exhausted, the orchestrator stops safely and explains the limit to the user.

## Operational references

- Security rules: [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md)
- Long-term direction: [ROADMAP.md](ROADMAP.md)
- Current work: [BACKLOG.md](BACKLOG.md)
- Vision coverage: [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md)
