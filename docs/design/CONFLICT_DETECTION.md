# Calendar conflict detection v1.1

## Status

- Status: Implemented
- Date: 2026-08-04
- Domain owner: Calendar projection over Calendar and Tasks & Projects
- Source of truth: `calendar_events`/configured calendar provider and `commitments`

## Product decision

Conflict detection is a read-only projection. It does not create a conflict
table, change event times, complete commitments, or silently modify user data.
It is exposed through the existing Calendar, Today/Personal State and Action
Center surfaces. Chat and Telegram use the same read-only assistant tool.

## v1 rules

1. An active commitment deadline inside a calendar event is a conflict.
2. Two different calendar events with overlapping time intervals are a conflict.
3. An explicit commitment-to-event relationship suppresses the first rule for
   that pair because the relationship is treated as intentional.
4. The default read-model horizon is 30 days; direct Calendar responses can
   evaluate the requested visible range.
5. External calendar reads respect the caller's `include_external` boundary;
   local calendar data remains available for the local-first dashboard.

## Calendar x Memory preference rules

The projection also reads only active, approved facts in the `preference` or
`habit` categories. The parser is intentionally deterministic and narrow:

1. Explicit `not before` / `not after` scheduling phrases produce earliest
   start or latest end warnings.
2. Explicit unavailable weekdays such as `not on Sundays` or `по воскресеньям
   не работаю` produce a weekday warning.
3. Unrecognised prose, pending facts, expired facts, notes, and arbitrary
   semantic guesses do not affect the calendar.
4. Exact time boundaries are allowed; warnings never move, reject, or rewrite
   an event by themselves.

## Surfaces

- Calendar event responses include `conflicts`; Today view shows the warning
  on the affected event and month/week pills are highlighted.
- Creating an event through the web Calendar performs the same read-only check
  before saving. A `409 calendar_conflicts` response opens a confirmation
  dialog; only an explicit save-anyway retry writes the event.
- Action Center emits `kind=conflict` items with a Calendar target and the
  existing priority model.
- Personal State includes conflict alerts and a `conflicts` count.
- `get_calendar_conflicts` is a GREEN assistant tool available to Chat and
  Telegram.

## Non-goals

- No automatic rescheduling or deletion.
- No new top-level page.
- No natural-language inference beyond the explicit deterministic patterns.
- Editing an existing event through the web form runs the same preflight and
  uses the same explicit save-anyway confirmation.

## Verification

- `backend/tests/test_conflict_service.py` covers deadline/event conflicts,
  overlapping events, and intentional links.
- `backend/tests/test_preference_conflict_service.py` covers approved-only
  extraction, time/day warnings, exact boundaries, and read-only draft preview.
- The central tool registry, backend tests, frontend lint and frontend build
  remain part of the release gate.
