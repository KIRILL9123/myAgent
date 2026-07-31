# Subscription Tracker Contract

Subscription Tracker records trial periods and recurring charges discovered from
email or entered manually. It is a separate domain from commitments and finance
transactions because its primary purpose is preventing unwanted renewals.

## Lifecycle

`PROPOSED -> ACTIVE -> CANCELLED / EXPIRED`

- Email analysis always creates `PROPOSED` records.
- A user must explicitly approve a proposal before reminders are enabled.
- Cancellation in the tracker only stops tracking. It never sends a cancellation
  request to a provider and never sends an email.
- `EXPIRED` is reserved for a completed trial/record that no longer needs tracking.

## Evidence and dates

Each record keeps its source type, source reference, confidence, and provenance.
The important dates are:

- `trial_ends_at` — when a free period ends;
- `next_charge_at` — the next known automatic charge;
- `reminder_at` — when the agent should warn the user.

If the email only states the trial end, the extractor must not invent a separate
charge date. When no reminder is provided, the service derives one seven days
before the known event (configurable with `SUBSCRIPTION_REMINDER_LEAD_DAYS`).

## Email scanning

The manual UI action and the daily scheduler scan unread messages through the
configured IMAP account without marking them read. Findings are deduplicated by a
stable email fingerprint. Marketing emails, one-time receipts, and vague offers
must be ignored by the extractor.

The scan is intentionally an approval-gated suggestion workflow. Provider pages,
cancellation links, and email bodies are untrusted external content and are never
treated as executable instructions.

## Current boundaries

Implemented in the MVP:

- SQLite entity and event history;
- email proposals and deduplication;
- manual entry;
- approve / stop tracking actions;
- Telegram reminders for active records;
- responsive web page at `/subscriptions`.

Planned follow-ups:

- search older mail, not only unread messages;
- connect reminders to calendar and Personal State Engine;
- unified approval-center projection for subscription proposals;
- provider-specific cancellation checklists, always requiring user confirmation.

Subscription proposals are now also projected into the shared Approval Center as
`SUBSCRIPTION` records. The dedicated subscription page remains available for
domain-specific details and reminder management.
