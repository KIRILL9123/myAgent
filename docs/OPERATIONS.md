# Operations and Reliability

This is the canonical operational guide. Detailed historical plans remain in
`docs/archive/` and are retained as design history.

## Runtime components

- FastAPI backend on port 8000.
- React/Vite dashboard served from `frontend/dist`.
- Bonsai OpenAI-compatible model server on `127.0.0.1:8080`.
- SQLite as the authoritative structured-state store.
- APScheduler for scheduled jobs and Telegram polling for notifications.

Host Control v1 exposes read-only diagnostics plus two approval-gated actions:
`open_url` and `open_path`. Local paths are limited to the project root and any
directories listed in `HOST_CONTROL_ALLOWED_ROOTS`. The Windows adapter uses the
native file/browser opener; the same contract is ready for a macOS adapter.

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

For a Windows always-on setup, install the user-level Scheduled Task once:
`powershell -ExecutionPolicy Bypass -File .\dev-tools\install_windows_tasks.ps1`.
It runs `run_backend_watchdog.ps1`, which restarts the backend after an unexpected
exit. Stop the watchdog cleanly by creating `logs\backend.stop`; remove the task with
`uninstall_windows_tasks.ps1`. Verify the service with
`powershell -File .\dev-tools\healthcheck.ps1 -CheckModel`.

For phone access, prefer serving the built dashboard from the backend on the same
origin (`http://<PC-LAN-IP>:8000`) and keep `HOME_AGENT_API_KEY` set to a random
long token. If Vite is served separately, add its exact origin to
`HOME_AGENT_ALLOWED_ORIGINS`. Plain LAN HTTP is acceptable only for temporary
trusted-home testing; for access outside the home network use a VPN such as
Tailscale or a reverse proxy with HTTPS. Do not expose port 8000 directly to the
public internet.

### Phone access preflight — 2026-08-05

The repository configuration is not considered phone-ready while the local
`.env` and `frontend/.env` contain the development placeholder API key. Before
opening the dashboard on a phone, replace both values with the same random long
token, verify the exact LAN origin, and restart the backend/frontend. The
cross-domain acceptance test intentionally remains local and dry-run; it does
not grant LAN access or contact Telegram/iCloud.

## Testing

- Unit and API suite: `pytest backend/tests -q`.
- Deterministic release gate: `python dev-tools/release_gate.py` (use `--backend-only` or
  `--frontend-only` for focused checks). It runs backend tests and frontend lint/build,
  returns a failing exit code on regression and appends a compact verdict to
  `logs/release_gate.jsonl`.
- CI must exercise the same release-critical checks as the local release gate. Any
  intentional difference must be documented in the reliability audit and in the
  workflow itself.
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

The current schema mechanism is the numbered SQL migration set in
`backend/app/storage/migrations`. `db.init_db()` records applied versions and runs
pending migrations during startup. Compatibility checks for legacy SQLite schemas remain.
The remaining reliability work is migration-parser coverage, rollback verification,
CI parity with the release gate, request budgets, and a tested recovery runbook.
Foreign-key enforcement, bounded document-upload cleanup, and notification delivery
bookkeeping were hardened in the 2026-08-04 reliability cycle. See
[RELIABILITY_AUDIT_2026-08-04.md](decisions/RELIABILITY_AUDIT_2026-08-04.md) for the
current order and acceptance criteria.

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

Document Vault artifacts are stored under `DOCUMENT_VAULT_DIR` (default:
`backend/document_vault`) while SQLite stores metadata and FTS5 chunk indexes.
Supported ingestion formats are TXT, Markdown, CSV, JSON, HTML and text-based PDF;
uploads are bounded to 20 MB and extracted text to 2 million characters. Document
content is treated as untrusted external data and is never promoted to a memory fact
automatically. Archive a document to remove it from retrieval without deleting its
metadata; backups must include the configured vault directory alongside SQLite.

## Request budgets

Each agent request should have maximum time, LLM calls, tool calls and tokens. When a
budget is exhausted, the orchestrator stops safely and explains the limit to the user.

## Operational references

- Security rules: [SECURITY_AND_SAFETY.md](SECURITY_AND_SAFETY.md)
- Long-term direction: [ROADMAP.md](ROADMAP.md)
- Current work: [BACKLOG.md](BACKLOG.md)
- Vision coverage: [MASTER_VISION_ALIGNMENT.md](MASTER_VISION_ALIGNMENT.md)
