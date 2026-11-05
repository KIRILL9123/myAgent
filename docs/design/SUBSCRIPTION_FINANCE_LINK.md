# Subscription → Finance Link

## Status

Implemented 2026-08-04 as a bounded v1.

## Contract

The subscription approval and the Finance approval are deliberately separate:

```text
PROPOSED subscription
  → approve tracking
  → ACTIVE subscription
  → SUBSCRIPTION_FINANCE_LINK proposal
  → approve Finance link
  → recurring Finance template
```

The link is stored in `subscription_finance_links`, not copied into either
domain. It is idempotent per subscription and keeps the approval id and
recurring-template id for provenance.

## Supported v1 boundary

- Only a known positive amount is linkable.
- Only `EUR` (or an omitted currency) is linkable by the current subscription-link
  policy. Finance now stores currency explicitly; expanding the link policy to
  other currencies remains a separate decision.
- Only an explicit monthly billing cycle is linkable.
- `next_charge_at` supplies the recurring template day of month.
- The link creates a recurring template in `Подписки`; it does not create an
  immediate transaction or perform a payment.
- Cancelling or expiring the subscription deactivates the linked template but
  preserves historical transactions.
- Annual, weekly, unknown-cycle, missing-date and non-EUR subscriptions remain
  tracked by Subscription Tracker without an automatic Finance proposal.

Recurring transaction generation now uses `source_template_id` for duplicate
prevention instead of comparing descriptions and amounts. This keeps two
similar subscriptions independent.

## UI placement

No new top-level page is introduced. The proposal appears in the existing
Approval Center and the subscription page explains that a second Finance
confirmation is waiting. After approval, the recurring template is visible in
Finance.

## Non-goals

- No automatic bank payment or provider cancellation.
- No currency conversion.
- No yearly/weekly recurrence until Finance has a generic recurrence contract.
- No deletion of ledger history on unlink.
