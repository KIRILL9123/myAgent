# Frontend UI System

## Purpose

The frontend uses a dark productivity-OS visual language for the local-first MyAgent workspace. The interface keeps all existing product areas, while prioritising state, approvals, and actions that require the user's attention.

## Current foundation

- `components/ui.tsx` contains shared buttons, cards, dialogs, loading, empty, error, and page-header states.
- `components/QueryProvider.tsx` owns the TanStack Query client and default retry/staleness behaviour.
- `api/client.ts` normalises API headers and errors through `ApiError`.
- State, Approval Center, Calendar, Mail, and Finance now use the shared request foundation. State, Approval Center, and Calendar are the reference screens for new layouts and interaction patterns.

## Interaction rules

- Destructive or consequential actions use an in-app dialog, never `window.confirm`.
- Recoverable request failures show an inline error with a retry action.
- Loading states must explain what is being loaded and must not block the whole page without a fallback.
- Icon-only controls require an accessible label.
- Cards that navigate must be keyboard reachable and expose a clear accessible name.

## Data rules

- New screens use TanStack Query with stable query keys and invalidation after mutations.
- Local state data is preferred for the initial State view so external mail/calendar failures cannot make the whole page unusable.
- Existing routes and backend contracts remain unchanged during the frontend migration.

## Migration order

1. State, Approval Center, Calendar, Dashboard, and shared shell.
2. Commitments and Subscriptions.
3. Memory, Chat, Deadlines, and System.
