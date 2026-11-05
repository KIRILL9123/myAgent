# Reliability and Documentation Audit — 2026-08-04

**Status:** accepted; hardening cycle completed 2026-08-05
**Scope:** local-first Mira; architecture, documentation consistency, backend reliability, and release verification.
**Decision:** do not add a new product domain until this bounded hardening cycle is complete.

## Executive conclusion

Mira already has a coherent domain spine: Dashboard/Today, Calendar, Commitments,
Finance, Memory, Documents, Chat, and the shared Action Center. The main risk is
no longer missing screens. It is drift between the documented contract and the
runtime behavior, plus a small set of safety and reliability gaps.

The bounded hardening cycle is now complete. The next cycle can open the
product-layer work already named in the architecture: Decision Journal and the
Goals → Projects → Tasks hierarchy. This remains intentionally scoped for a
personal local project: no enterprise infrastructure, multi-tenant redesign,
or new top-level navigation is required.

## Findings

| Priority | Finding | Evidence | Decision |
|---|---|---|---|
| P0 | Documentation contains contradictory status and stale implementation notes. | `BACKLOG.md`, `SUBSCRIPTION_FINANCE_LINK.md` | Reconcile status before selecting the next product feature. `MEMORY_EVOLUTION.md` correctly keeps its not-yet-implemented temporal/decay fields as future work. |
| P0 | CI runs less than the local release gate. | `.github/workflows/ci.yml`, `dev-tools/release_gate.py` | Make CI and the release gate check the same deterministic baseline. |
| P1 | SQLite connections do not explicitly enable foreign-key enforcement. | `backend/app/storage/db.py` and migrations using `REFERENCES` / cascades | Add connection-level FK enforcement and regression coverage. |
| P1 | Pending-action expiry is nullable and new actions do not receive an explicit expiry. | `003_pending_actions.sql`, `backend/app/storage/db.py` | Give confirmation records a bounded lifetime and test expired/replay paths. |
| P1 | Document upload reads the entire payload before enforcing the configured bound; concurrent dedupe can leave an orphan file. | `backend/app/api/documents.py`, `backend/app/documents/document_service.py` | Add bounded upload handling, conflict-safe cleanup, and concurrency tests. |
| P1 | Notification coalescing settings and delivery bookkeeping need a behavior-level regression test. | `019_notification_delivery.sql`, `backend/app/notifications/delivery_service.py` | Verify that only delivered items are marked delivered and that the configured policy is applied. |
| P1 | “New conversation” navigates to Chat without resetting the session id. | `frontend/src/components/AppShell.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/ChatPage.tsx` | Make a new conversation create a fresh session while preserving ordinary Chat navigation. |
| P1 | Finance presentation can show a selected currency as EUR and recurring income with expense semantics. | `frontend/src/pages/FinancePage.tsx`, `frontend/src/components/finance/RecurringTemplateCard.tsx` | Fixed 2026-08-04; keep amount, currency, and income/expense labels derived from the same domain contract. |
| P2 | Dashboard and Notification Center read different action feeds. | `frontend/src/components/TodayOverviewWidget.tsx`, `frontend/src/pages/NotificationsPage.tsx`, `frontend/src/api/state.ts`, `frontend/src/api/actions.ts` | Fixed 2026-08-04; reuse one Action Center contract for projections and do not create a second notification/task store. |
| P2 | Tablet navigation and Memory Graph error states still need a focused responsive pass. | `frontend/src/index.css`, `frontend/src/components/AppShell.tsx`, `frontend/src/components/MemoryGraph.tsx` | Schedule after the contract fixes; keep this separate from domain work. |
| P2 | Decision Journal and Goals → Projects → Tasks remain the largest product-layer gap. | `PRODUCT_ARCHITECTURE.md`, `docs/design/TASK_FLOW.md` | Start only after the hardening cycle. |
| P2 | OCR is the best next document capability, but should remain a bounded adapter. | `docs/decisions/OSS_AUDIT_2026-08-04.md`, `docs/ROADMAP.md` | Schedule after reliability work; do not embed a complete OSS product. |

## Progress as of 2026-08-04

- [x] Reconciled the status contradictions and stale Finance wording in the
  active planning documents.
- [x] Enabled SQLite foreign keys for new connections and added a 15-minute TTL
  for newly created pending confirmations, preserving old nullable records.
- [x] Added bounded upload reads and conflict-safe Document Vault cleanup.
- [x] Fixed calendar notification bookkeeping and applied the configured
  coalesce window.
- [x] Fixed the “New conversation” session reset and verified the frontend build.
- [x] Align CI with the full local release gate; the workflow now installs the
  frontend lockfile and invokes `python dev-tools/release_gate.py`. A remote
  GitHub Actions run is still the final environment check.
- [x] Fix Finance currency/direction presentation and unify Dashboard/Notification
  Center action-feed contracts.
- [x] Add a temporary-DB cross-domain smoke test covering Tool Registry → Calendar,
  Finance, Commitments → Action Center → notification dry-run:
  `backend/tests/test_cross_domain_integration.py`.
- [ ] Phone/LAN access remains a deployment gate until the local `.env` and
  `frontend/.env` replace their placeholder API keys with one random long token.

## Implementation order

1. Reconcile the documentation and open the active backlog cycle. **Done.**
2. Add regression tests for FK enforcement, confirmation expiry, bounded upload,
   concurrent document dedupe, and notification delivery bookkeeping. **Done.**
3. Implement the smallest safe fixes and run the relevant tests. **Done.**
4. Align CI with `python dev-tools/release_gate.py`. **Done.**
5. Reassess the product backlog and open Decision Journal/Projects. **Done;
   next product cycle is recorded in `BACKLOG.md`.**

## Acceptance criteria

- Documentation has one status for every completed audit item.
- A fresh SQLite connection enforces declared foreign keys.
- A pending confirmation cannot be claimed after its expiry and cannot be replayed.
- Oversized or failed document uploads do not create orphan files.
- Notification delivery marks only successfully delivered items and respects the
  configured batching/coalescing policy.
- “New conversation” creates a fresh Chat session.
- Finance displays the selected currency and recurring income/expense direction
  consistently.
- CI exercises the same release-critical checks as the local release gate.
- The cross-domain smoke test proves that registry-dispatched local writes are
  visible to Action Center and notification dry-run without external delivery.
- No new top-level domain or duplicate task/notification subsystem is introduced.

## References

- [Product architecture](../../PRODUCT_ARCHITECTURE.md)
- [Roadmap](../ROADMAP.md)
- [Backlog](../BACKLOG.md)
- [Operations](../OPERATIONS.md)
- [OSS audit](OSS_AUDIT_2026-08-04.md)
