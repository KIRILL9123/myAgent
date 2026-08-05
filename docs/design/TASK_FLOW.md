# Task Flow v1

Status: **implemented 2026-08-04**
Owner: Tasks & Projects domain, currently backed by the existing Commitment entity

## Product placement

Mira does not create a second `tasks` table. A personal task is the simple user
language for an active Commitment. Commitments extracted from email or documents
still use the proposal and approval lifecycle; an explicit command from the user
in Chat or Telegram is sufficient to create an active personal task.

The existing `/commitments` page remains the management surface. Today,
Calendar, Action Center, and Telegram reminders consume the same Commitment
record rather than receiving copied task state.

## Assistant contract

The shared tool registry exposes the following parity contract to Chat and
Telegram:

- `list_tasks` — list open tasks or a requested lifecycle status and resolve the
  exact task ID;
- `create_task` — create an active task with an optional deadline and reminder;
- `reschedule_task` — update the deadline and optionally the reminder by exact ID;
- `complete_task` — mark an active task completed by exact ID;
- `cancel_task` — cancel a task by exact ID.

All five tools are GREEN because they modify only Mira's local personal state
after an explicit user request. Tool calls are still validated, audited, and
executed through the central registry.

## Cross-domain behavior

- A deadline or due reminder is projected into Today and Action Center.
- An active task reminder is eligible for the existing Telegram delivery job.
- A calendar event can be created with `commitment_id` to create an explicit
  Calendar ↔ Commitment link.
- The link does not complete the task automatically when the event ends.
- Rescheduling changes the Commitment deadline and preserves calendar links.
- Completing or cancelling a task does not delete or mutate its calendar event.

When a user names an existing task without its ID, Mira first calls
`list_tasks`. The assistant must never guess an ID or mark a task complete only
because a related calendar event has passed.

## Future project hierarchy reference

Super Productivity and Vikunja are useful references for timeboxing, project
grouping, recurring views and Goals → Projects → Tasks navigation. They do not
justify a second task system. Any future hierarchy must extend the existing
Commitment-backed flow, preserve explicit Calendar links and keep Today/Action
Center as projections. The source and license assessment is recorded in
[OSS_AUDIT_2026-08-04.md](../decisions/OSS_AUDIT_2026-08-04.md).

## Explicit boundaries

This version does not add project entities, subtasks, dependencies, recurring
tasks, automatic event creation, or automatic completion. The long-term
`Goals → Projects → Tasks → Commitments` hierarchy remains a separate proposal
and is not silently introduced by this task flow.

## Verification

`backend/tests/test_task_tools.py` covers active creation, list visibility,
rescheduling, completion, cancellation, and explicit Calendar linking. Existing
Commitment, Action Center, state, reminder, tool-schema, and full release-gate
tests remain part of the regression suite.
