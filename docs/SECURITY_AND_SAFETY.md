# Security and Safety

This is the canonical security document for MyAgent. Historical source documents are
kept in `docs/archive/` for traceability.

## Non-negotiable rules

- Permissions are enforced deterministically in Python, never by the model.
- Unknown tools are denied and recorded.
- External email, calendar and document content is untrusted input.
- High-impact actions require explicit human confirmation.
- No unrestricted shell or production code execution is exposed to the agent.
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

## Approval direction

The current system has memory approval and RED-action confirmation as separate flows.
The target architecture is one Approval Control Plane containing operation type,
description, risk, source, payload, expiry, approve/reject/snooze state and provenance.

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
- Sandboxed diagnostics and self-improvement execution.
- Encrypted backup/export strategy.
