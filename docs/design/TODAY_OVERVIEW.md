# Today Overview v2

Status: **implemented 2026-08-04**
Owner: Today projection, backed by Personal State

## Product placement

Today is the personal operating overview, not a new domain, database table,
task model, calendar, or notification type. The canonical route is `/dashboard`.
The page gives Mira one calm answer to “what matters now?” and links back to
the owning domain for every mutation or deeper review.

## Read model

The overview consumes the existing read-only `GET /api/state/` snapshot. It
shows only a compact operational slice:

- today’s calendar events, including conflict indicators;
- active tasks backed by existing Commitments;
- deadlines inside the next 30 days;
- attention items and next actions from Action Center / Personal State;
- small secondary links to Calendar, Finance, Deadlines, and Mail.

Today does not copy or mutate domain records. Calendar events, Commitments,
Finance, Mail, and Action Center remain the sources of truth.

## Runtime contract

`DashboardPage` uses one React Query snapshot with a short freshness window.
The page does not add separate dashboard requests for Calendar, Finance,
deadlines, or Mail. Refresh and retry operate on that same snapshot, while
domain pages remain responsible for their own detailed data and mutations.

## Interaction states

- **Loading:** preserve the layout with a compact skeleton.
- **Ready:** show the health headline, metrics, today’s schedule, next actions,
  and active tasks.
- **Empty:** say explicitly when the day is free or there are no active tasks.
- **Attention:** use the existing warning color only for real pending signals.
- **Error:** keep the shell usable and provide one retry action.
- **Details:** links navigate to the owning route; Today can complete an active
  task, while rescheduling remains an explicit Commitment operation.

## Design rules

1. Keep Today above supporting domain cards in the hierarchy.
2. Prefer one unified snapshot over a collection of independently loading cards.
3. Do not introduce a top-level route for a new projection.
4. Do not duplicate a task, event, subscription, or notification entity.
5. Keep the overview useful on narrow screens without hiding the primary signal.
6. Keep projection controls compact; domain mutations must remain owned by the
   existing Calendar, Commitment, Finance, or approval services.

## Verification

The implementation was smoke-checked at `/dashboard` on 2026-08-04. The page
rendered the Today region from the state snapshot and browser console errors
were empty. `npm run lint`, `npm run build`, and the repository release gate
remain the final regression checks for this change.
