# Security and Safety

This is the canonical security document for Mira. Historical source documents are
kept in `docs/archive/` for traceability.

## Non-negotiable rules

- Permissions are enforced deterministically in Python, never by the model.
- Unknown tools are denied and recorded.
- External email, calendar and document content is untrusted input.
- High-impact actions require explicit human confirmation.
- No unrestricted shell or production code execution is exposed to the agent.
- Host control v1 is limited to read-only diagnostics and approval-gated opening of
  HTTP/HTTPS URLs or paths under configured roots; process termination, shutdown and
  arbitrary command execution are not available.
- Secrets stay in environment/configuration boundaries and are never placed in prompts.
- New autonomous behavior starts in observe/shadow mode before approval-gated automation.
- Destructive schema or data changes require backup, migration review and rollback planning.

## Action safety model

| Level | Meaning | Examples |
|---|---|---|
| Green | Read-only or reversible | Read calendar, search email, inspect memory |
| Yellow | State-changing but reviewable | Add transaction, create reminder |
| Red | High-impact or external side effect | Send email, modify/delete calendar event |

The orchestrator validates tool arguments with Pydantic, checks permission level, applies
dry-run rules, requests confirmation for RED actions, executes only after approval, and
writes an audit record.

## Dry-run and shadow mode

`EXECUTION_MODE=dry_run` must return a `would_do` description without real external I/O.
Shadow mode records what the agent would have done and exposes it for comparison without
executing it. Automation may be enabled only after evaluation and explicit approval.

## Audit findings recorded 2026-08-03

- `.env.example` safety was fixed on 2026-08-03: a fresh personal install starts in local `dry_run`, uses the local calendar, disables subscription scans, leaves the API key blank, and requires deliberate opt-in for external side effects.
- Manual integration scripts were fixed on 2026-08-03: `pytest.ini` restricts discovery to `backend/tests` and excludes `dev-tools`; the credential configuration check reports presence only and never prints secret values. Live scripts remain available for intentional personal diagnostics.
- Permission drift was fixed on 2026-08-03: the runtime now reads permission levels from `backend/app/agent/tool_registry.py`; `dev-tools/check_tool_registry.py` validates coverage.
- Temporal consistency was fixed on 2026-08-03: cross-domain read models now receive one reference instant and configured user timezone, preventing machine-local date boundaries from changing what Today or Telegram considers due.
- Pending-action confirmation hardening was fixed on 2026-08-03: atomic claim/cancel operations bind nonce, source channel and chat/session identity; Telegram callback action ids participate in lookup; expiry, replay, wrong-chat, cross-channel and concurrent-claim paths have regression coverage; failure reasons and resolution timestamps are persisted.
- Async I/O boundary was fixed on 2026-08-03: CalDAV, IMAP, document work, subscription scans, State/Action Center aggregation and scheduled summary reads use the shared thread boundary. This prevents external timeouts or PDF parsing from starving the event loop.

The latest documented release gate remains green in the project environment (`220 passed, 2 skipped, 1 warning`); calendar provider selection, dry-run boundaries, async I/O boundaries, confirmation audit invariants, personal-install safety defaults, document proposals and cross-domain conflict checks have focused regression coverage.

## Approval direction

The Approval Control Plane now covers memory, commitments, subscriptions, document
proposals, RED actions and reviewed sandbox-apply requests. A sandbox apply is still two-step: a RED request
may create the proposal, and the final repository mutation requires a separate approval
record with conflict checks and rollback backup.

## Required test coverage

- RED confirmation cannot be bypassed.
- SMTP, CalDAV and Telegram tests use fake transports.
- Dry-run and scheduler tests prove zero real side effects.
- Prompt-injection and malicious external-content cases are tested.
- Malformed and unknown tool arguments are denied safely.
- Backup restore and migration paths are tested before schema changes.

## Future security work

- Capability tokens scoped by action, payload and expiry.
- Per-domain autonomy levels.
- Adversarial corpus for prompt injection, poisoned memory and malicious tool arguments.
- Broader adversarial evaluation of sandboxed diagnostics and self-improvement execution.
- Encrypted backup/export strategy.
