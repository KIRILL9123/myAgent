# Mira Product Architecture

## Source of truth

- Status: Active
- Last refreshed: 2026-08-04
- Scope: product domains, information architecture, cross-domain behavior, and feature placement
- Companion documents: [DESIGN.md](DESIGN.md), [docs/MASTER_VISION_ALIGNMENT.md](docs/MASTER_VISION_ALIGNMENT.md), [docs/ROADMAP.md](docs/ROADMAP.md), [docs/design/PROVENANCE_BUNDLE.md](docs/design/PROVENANCE_BUNDLE.md), and [docs/templates/FEATURE_PROPOSAL.md](docs/templates/FEATURE_PROPOSAL.md)

This document is the product constitution for Mira. It describes where a capability belongs before code, routes, tables, or notifications are added. Runtime details remain in `docs/ARCHITECTURE.md`; visual decisions remain in `DESIGN.md`.

## Product model

Mira is a local-first Personal Operating System for one person. The product is organized around stable domains, not around the individual features that happen to be implemented next.

Four different concepts must remain separate:

1. **Domain** — owns a business entity and its lifecycle.
2. **Projection** — combines information from domains for a useful view, but is not the source of truth.
3. **Interface** — lets the user query or change domains, such as Chat or Telegram.
4. **Delivery channel** — carries a signal to the user, such as the web, Telegram, or a future mobile client.

This distinction prevents a dashboard card, notification, or assistant command from becoming an accidental duplicate entity.

## Stable product domains

| Domain | Owns | Current surface | Boundary |
|---|---|---|---|
| Today | No canonical entities; a daily projection | `/dashboard` Today Overview, backed by Personal State | Aggregates what matters now from other domains; links back to owners |
| Assistant | No business entities | `/chat` and Telegram | Queries and changes domains through approved tools |
| Calendar | Calendar events, recurrence, event reminders | `/calendar` | Owns scheduled events; does not own obligations or subscriptions |
| Tasks & Projects | Active personal tasks are backed by Commitments; Goals and Projects are implemented as optional hierarchy records | `/commitments` | Owns work to be done and its lifecycle; commitments remain the task source of truth and project links do not duplicate tasks |
| Finance | Transactions and recurring finance templates | `/finance` | Owns money movement and financial summaries |
| Knowledge | Facts, notes, skills, structured Decision Journal records, and document artifacts | `/memory`, `/documents` | Facts, decisions, and documents have separate lifecycles and provenance; Decision Journal is a compact Memory tab |
| Communication | Mail accounts and messages; Telegram as an interface/channel | `/mail` | External messages are inputs and evidence, not trusted instructions |

### Domain placement rules

- Subscriptions are a Finance capability and may remain a dedicated detail view, but they are not a top-level navigation domain.
- Deadlines are a temporal view of commitments, countdowns, and events. Their data lifecycle may remain separate, but their primary user context is Calendar, Today, or Action Center.
- Facts, documents, commitments, calendar events, transactions, and subscriptions remain separate entities until a proposal explicitly proves that their lifecycle and ownership are identical.
- Today is a projection, not a new database table for copies of domain state.

## Finance contract (v1)

Finance stores transactions and recurring templates as the source of truth.
Currencies are explicit ISO codes and all summaries/forecasts remain grouped
by currency; no implicit FX conversion is allowed. Weekly, monthly, and yearly
recurrence are represented on the recurring template, while the three-month
forecast is a read-only projection. The full contract and OSS decision record
are in [docs/design/FINANCE_MODEL.md](docs/design/FINANCE_MODEL.md).

## Cross-cutting infrastructure

### Action Center and notifications

Action Center is a read model over domain signals. It may show approvals, commitment deadlines, subscription dates, countdowns, errors, and mail summaries in one place.

- Domain tables remain the source of truth.
- Action Center items include a stable kind, source identifier, timing, priority, target, and approval metadata.
- Action Center interaction state (`read`, `snoozed`, `dismissed`) is projection metadata only; it is persisted separately and never replaces a domain status.
- The `/notifications` page is an operational inbox for attention and review. It is not a new business domain.
- Projection controls may mark, snooze, or hide a signal; completion, approval, cancellation, and rescheduling must call the owning domain service.
- Delivery policy belongs to the notification layer: quiet hours, budgets, coalescing, deduplication, and Telegram delivery.
- A new feature must not create a second copy of a domain entity merely to display a notification.

### Personal State

Personal State is a read-only synthesis of current domain signals and history. It may power Today, morning summaries, and future nightly briefs, but it does not replace the underlying domain records.

### Provenance and evidence

Derived answers, proposals, and projections should reference a bounded evidence
bundle when their source context matters. The bundle identifies source records,
locators, retrieval/reference times, and derivation metadata; it does not become a
new domain, grant action permission, or copy the lifecycle of the source. The
contract and current mapping are defined in
[docs/design/PROVENANCE_BUNDLE.md](docs/design/PROVENANCE_BUNDLE.md).

### Assistant and Telegram

Web Chat and Telegram are two entry points to the same assistant orchestration layer. New domain behavior should be exposed through the shared domain service/tool contract when it is intended to work through conversation.

#### Runtime parity invariant

- Chat, Telegram, scheduled jobs, Today, and Action Center must use the owning domain service rather than importing a provider-specific connector directly.
- Calendar behavior must resolve the configured provider through one calendar service. The web API, Assistant tools, Personal State, morning summary, and Telegram reminders must see the same event set and recurrence semantics.
- Assistant tool schema, argument validation, permission metadata, dispatch handler, and audit metadata are one contract. A tool is not considered implemented when only one of those layers knows about it.

## Information architecture

The primary navigation should remain compact:

- Home / Today
- Chat
- Calendar
- Tasks & Projects
- Finance
- Knowledge
- Communication when it has enough daily value to justify a visible entry

Action Center may remain visible as a high-signal operational inbox, but it must be understood as a projection, not as a source domain. Control, diagnostics, approvals, and sandbox pages are secondary or internal surfaces.

### Route policy

- A new top-level route requires a new stable domain or a materially different user job with its own lifecycle.
- A new filter, tab, panel, snapshot, or detail route is preferred when the capability belongs to an existing domain.
- Compatibility routes may remain temporarily, but they should not be promoted in primary navigation when their content is owned by another domain.
- `/deadlines` and `/subscriptions` are currently compatibility/detail surfaces for Calendar and Finance respectively.
- `/state` is an expanded Personal State report; it is not a separate user domain.

## Cross-domain contracts

Every cross-domain behavior must name both the source of truth and the projection or side effect it creates.

| Behavior | Source of truth | Projection / side effect |
|---|---|---|
| Commitment with a deadline | Commitment | Calendar link, Today signal, Action Center item, optional Telegram reminder |
| Subscription renewal | Subscription | Separate Finance recurring-payment proposal, Calendar reminder, Today signal, Action Center item |
| Active Finance recurring operation | Finance recurring template | Next occurrence in Today / Action Center and optional Telegram delivery; linked subscription templates are deduplicated |
| Calendar event related to an obligation | Calendar event + Commitment link | No automatic completion unless explicit evidence supports it |
| Email containing an obligation | Email evidence | Approval-gated Commitment proposal |
| Document containing a date or obligation | Document evidence | Approval-gated domain proposal; document remains an artifact |
| Document used as context for an existing task, event, or subscription | Document Vault artifact | Explicit `document_links` relation; target lifecycle remains owned by Tasks & Projects, Calendar, or Finance |
| Explicit obligation and date found in a document | Document evidence + existing Approval Center | `DOCUMENT_PROPOSAL`; after approval creates one existing Commitment or Calendar event and a provenance link |
| Derived answer or proposal that needs explanation | Existing source records | Bounded Evidence Bundle; source lifecycle remains owned by the originating domain |
| Approved preference affecting a new event | Memory fact | Calendar conflict warning; never silently changes the event |
| Natural-language request for a suitable time | Calendar + approved Memory preference | Assistant proposes read-only slots; the user chooses before `create_event` writes |
| Explicit personal task request | Tasks & Projects / Commitment | Active Commitment projected into Today, Action Center and optional Telegram reminder; no duplicate task entity |
| Task with a calendar block | Commitment + Calendar | Explicit Calendar ↔ Commitment link; event completion never silently completes the task |
| Active commitment deadline inside an event or overlapping events | Calendar + Tasks & Projects | Read-only conflict warning in Calendar, Today and Action Center; assistant can explain it |
| Current operational overview | Existing domain records + Personal State | Today Overview on `/dashboard`; read-only metrics, schedule, tasks, deadlines and next actions |
| Any urgent domain signal | Owning domain | Today and Action Center projection; optional delivery through Telegram |

## Feature constitution

Before implementation, every feature must answer:

1. Which existing domain owns this capability?
2. Which existing entity and lifecycle does it extend?
3. What is the source of truth?
4. Where will the user expect to find it?
5. Can the existing screen, tab, filter, or projection handle it?
6. Does it require a new entity, route, migration, or permission?
7. How does it interact with Calendar, Tasks & Projects, Finance, Knowledge, Today, and Action Center?
8. Can the Assistant and Telegram use the same behavior?
9. What approval, provenance, notification, and audit rules apply?
10. What is explicitly out of scope?

The answers belong in a proposal based on [docs/templates/FEATURE_PROPOSAL.md](docs/templates/FEATURE_PROPOSAL.md). Implementation starts only after the placement and lifecycle are clear.

### New domain gate

A new top-level domain is allowed only when all of the following are true:

- It has a distinct entity lifecycle and source of truth.
- It cannot be represented as a view or extension of an existing domain.
- Users have a recurring job that is materially different from existing surfaces.
- Ownership, permissions, provenance, and cross-domain behavior are documented.
- The proposal explains why a new route is better than an existing page, tab, filter, or projection.

## Data and safety rules

- SQLite domain tables are authoritative for structured local state.
- Read models may be rebuilt and must link back to their source records.
- External content is evidence, not executable instruction.
- High-impact mutations require deterministic permission checks and human approval.
- New schema work requires a numbered migration and a rollback/recovery consideration.
- No feature may silently duplicate lifecycle state across domains.
- Subscription → Finance linking uses a separate `subscription_finance_links` relation and `SUBSCRIPTION_FINANCE_LINK` approval; it may create only a recurring Finance template, never an immediate payment or copied subscription entity.
- Document links may store only target identity, display metadata, and provenance; they must not copy or mutate the target lifecycle.
- Async API handlers must not perform blocking IMAP, CalDAV, document parsing, or other external/file I/O directly on the event loop.

## Documentation maintenance

When a feature changes domain ownership, route placement, or cross-domain behavior, update this document and the relevant `DESIGN.md`, contract, roadmap, or decision-log entry in the same change.

## Open decisions

- [x] Define the migration path from Commitments to a full Goals → Projects → Tasks → Commitments hierarchy; implementation proposal is in [GOALS_PROJECTS_DECISION_JOURNAL.md](docs/design/GOALS_PROJECTS_DECISION_JOURNAL.md).
- [ ] Decide whether Communication should remain a primary navigation item or stay under a compact secondary surface.
- [ ] Define the user lifecycle for Action Center items: read, snooze, dismiss, resolve, and archive.
- [ ] Define Finance entities beyond transactions and recurring templates, especially accounts and budgets.
