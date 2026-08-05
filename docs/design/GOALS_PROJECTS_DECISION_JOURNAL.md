# Goals, Projects & Decision Journal — Feature Proposal

## Status

- Status: Implemented v1
- Date: 2026-08-05
- Owner: Mira personal workspace
- Related backlog: `docs/BACKLOG.md` — Active Product Cycle

## 1. Feature

Mira currently has active Commitment-backed tasks, but no durable hierarchy for
why the work exists or which project owns it. It also has facts and notes, but
no explicit journal for important decisions and their rationale.

Desired outcome: the user can say “это относится к проекту X”, see progress in
Today, and later ask “почему мы решили так?” without creating a second task or
notification system.

## 2. Domain placement

- Goals, Projects and task links belong to the existing **Tasks & Projects**
  domain.
- The Decision Journal belongs to the existing **Knowledge** domain as a
  structured decision record, not as a new top-level domain.
- No new top-level navigation route is required. `/commitments` becomes the
  compatibility entry for Tasks & Projects; Decision Journal is a tab inside
  `/memory` or a compact Knowledge detail view.

## 3. Existing entities affected

- `commitments` remains the source of truth for active tasks and lifecycle
  transitions.
- `Action Center`, Today and Telegram continue to project commitment signals;
  they do not receive copied task rows.
- Existing provenance/evidence rules in
  [`PROVENANCE_BUNDLE.md`](PROVENANCE_BUNDLE.md) apply to decisions and
  derived proposals.

## 4. New entity decision

New entities are required because a goal/project has a lifecycle and ownership
that is not the same as a task, and a decision is not a memory fact.

### Goal

- `id`, `title`, `description`, `status`, `target_date`, `created_at`,
  `updated_at`, `provenance_json`
- Statuses: `ACTIVE → COMPLETED`, with `PAUSED` and `ARCHIVED` as reversible
  states.

### Project

- `id`, `goal_id` (optional), `title`, `description`, `status`, `start_date`,
  `target_date`, timestamps, `provenance_json`
- Statuses: `PLANNED → ACTIVE → COMPLETED`, with `PAUSED` and `ARCHIVED`.
- A project is the only new owner link for tasks in the first slice:
  `commitments.project_id` is nullable and does not change Commitment status.

### Decision

- `id`, `title`, `decision_text`, `rationale`, `alternatives_json`, `status`,
  `decided_at`, `review_at`, `source_type`, `provenance_json`,
  `evidence_bundle_json`, timestamps
- Statuses: `ACTIVE`, `REVISIT`, `SUPERSEDED`, `ARCHIVED`.
- Decisions are explicit records; Mira must not turn an inferred answer into a
  decision without an explicit user request or approval.

## 5. User interface placement

- `/commitments`: add compact Goals and Projects tabs while keeping current
  task operations intact.
- `/memory`: add a Decision Journal tab; do not create another top-level
  sidebar item.
- Chat and Telegram are first-class entry points for creating, listing,
  linking, completing and revisiting these records.
- Empty states explain that a goal/project/decision can be created from the
  current screen or through Chat.

## 6. Cross-domain behavior

- **Calendar:** goal/project target dates are read-only planning signals in v1;
  no calendar event is created automatically. A user can explicitly create an
  event and link it where the existing task-calendar contract supports it.
- **Tasks & Projects:** a task remains a Commitment; `project_id` is a link,
  not a replacement table or new task lifecycle.
- **Finance:** no automatic project budgets or transaction tagging in v1.
- **Knowledge / Memory:** decisions are structured knowledge; facts and
  documents remain separate entities and may be evidence sources.
- **Today / Personal State:** show goal/project progress only as a compact
  projection; existing active tasks and deadlines remain the actionable items.
- **Action Center:** only due tasks, approvals, conflicts or explicit review
  dates become actions; project rows are not copied into the feed.

## 7. Assistant and delivery

- Chat and Telegram use the same Tool Registry models, permissions, handlers
  and domain services.
- Explicit commands such as “создай проект” or “запиши решение” create records
  directly at the lowest safe permission level.
- Derived suggestions from documents, email or memory become approval-gated
  proposals and never silently create a goal, project or decision.
- Decision review reminders are low/medium priority, respect quiet hours and
  use existing delivery deduplication.

## 8. Safety and provenance

- External mail, documents and web content are evidence only.
- Explicit user-created records use the current channel/session as provenance.
- A decision must retain rationale and alternatives when supplied; editing a
  decision creates an audit event rather than silently replacing history.
- Mira must never mark a task complete because a project or goal changed state.

## 9. Data and API impact

- Add one numbered migration for `goals`, `projects`, `decisions`, and the
  nullable `commitments.project_id` link, with indexes and foreign keys.
- Add domain services first, then API endpoints and shared Assistant/Telegram
  tools through the registry.
- Add read-only project/goal summaries to existing Today/Action Center
  contracts only when they can link back to the owner record.
- Rollback is additive: archive or remove only empty new records during
  development; preserve existing commitments and facts.

## 10. Non-goals

- No Jira/Notion-style full project management suite.
- No automatic task generation from vague assistant text.
- No budgets, time tracking, Kanban board, team collaboration or recurring
  project automation in the first slice.
- No new top-level “Goals”, “Projects” or “Decisions” sidebar modules.

## v1 implementation record

Implemented on 2026-08-05:

- migration `032_goals_projects_decisions.sql` adds `goals`, `projects`,
  `decisions`, and the nullable `commitments.project_id` relationship;
- `backend/app/planning/planning_service.py` owns goal/project lifecycle and
  task linking; `backend/app/memory/decision_service.py` owns journal records;
- `/api/planning` and `/api/memory/decisions` expose the same explicit-record
  operations used by the web UI;
- the shared Chat/Telegram Tool Registry now exposes ten green tools for
  goals, projects, task linking and decisions;
- `/commitments` has compact Tasks, Goals and Projects tabs; `/memory` has a
  compact Decisions tab. No new top-level route was added;
- no automatic Calendar, Finance, Notification or external-provider side
  effects are created by these records.

The implementation is intentionally bounded: project links are one-way from
an existing Commitment to a Project, and Decision Journal records are manual
or explicit assistant actions. Future derived proposals still require the
existing Approval Center.

## 11. Acceptance criteria

- A goal can own projects, and a project can link existing active tasks without
  duplicating them.
- Existing task lifecycle and Action Center behavior remain unchanged.
- Chat and Telegram expose the same create/list/link/revisit behavior.
- A decision can be created, listed and marked for revisit with rationale and
  provenance intact.
- Today and Action Center show links to source records rather than copied
  entities.
- Migration, service, API, registry, frontend and documentation tests pass.

## Decision

- Decision: implement this as the next product cycle after reliability closure.
- Rationale: it gives Mira durable direction and context while preserving the
  existing domain boundaries and personal local-first scope.
- Follow-up documentation: update `PRODUCT_ARCHITECTURE.md`, `ROADMAP.md`,
  `MASTER_VISION_ALIGNMENT.md`, and `DECISION_LOG.md` with the implementation
  status in the same change as the first migration.
