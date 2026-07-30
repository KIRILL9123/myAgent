# Operations and Reliability

This is the canonical operational guide. Detailed historical plans remain in
`docs/archive/` and are retained as design history.

## Runtime components

- FastAPI backend on port 8000.
- React/Vite dashboard served from `frontend/dist`.
- Bonsai OpenAI-compatible model server on `127.0.0.1:8080`.
- SQLite as the authoritative structured-state store.
- APScheduler for scheduled jobs and Telegram polling for notifications.

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

The dashboard should eventually expose request count, failures, RED actions, tool calls
and average latency for the last 24 hours.

## Request budgets

Each agent request should have maximum time, LLM calls, tool calls and tokens. When a
budget is exhausted, the orchestrator stops safely and explains the limit to the user.

## Operational references

- Security rules: [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md)
- Long-term direction: [ROADMAP.md](ROADMAP.md)
- Current work: [BACKLOG.md](BACKLOG.md)
- Vision coverage: [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md)
