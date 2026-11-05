# Finance model v1

Status: active, implemented 2026-08-04.

Finance remains one personal domain. Transactions and recurring templates are
the source of truth; the forecast is a read-only projection over active
templates. Subscriptions can create a template only through the existing
approval-gated link flow.

## Currency contract

- Every transaction and recurring template stores an ISO-4217 three-letter
  currency code in `currency`.
- The UI currently offers EUR, USD, GBP and UAH; the backend validates the
  general three-letter-code shape so the personal database can grow without a
  schema change.
- Summaries and forecasts group totals by currency. They never add EUR, USD,
  or another currency together without an explicit exchange-rate record.
- `FINANCE_DEFAULT_CURRENCY` selects the display currency when it is present;
  otherwise the first currency in the result is used for legacy scalar summary
  fields. The grouped `by_currency` object is authoritative.
- FX conversion, accounts, budgets, and exchange-rate history are explicitly
  out of scope for this slice. This keeps the local personal workflow honest
  instead of showing a misleading single balance.

## Recurrence contract

Recurring Finance templates support exactly three explicit frequencies:

- `weekly`: `day_of_week` uses Python's Monday=0 through Sunday=6 convention.
- `monthly`: `day_of_month` is clamped to the last day of shorter months.
- `yearly`: `month_of_year` plus `day_of_month`; February 29 is clamped in
  non-leap years.

Generated transactions retain `source_template_id`. Processing is idempotent
within the frequency period, so rerunning the scheduler cannot create a second
transaction for the same template period. A stopped template remains visible
as inactive history and no longer contributes to future projections.

## Forecast contract

`GET /api/finance/forecast?months=3` returns a three-calendar-month read model:

- grouped totals in `by_currency`;
- each concrete occurrence with date, type, amount, currency and source
  template id;
- no historical ledger mutation and no currency conversion.

The Finance page loads this projection together with the current journal and
recurring templates, so the next few months are available immediately after
the initial request.

## Assistant and Telegram contract

The web Chat and Telegram channel use the same Finance tool definitions and
handlers. The shared contract is documented in
[FINANCE_ASSISTANT.md](FINANCE_ASSISTANT.md); it covers one-off transactions,
read-only journal/summary/forecast queries, and explicitly requested recurring
templates. This keeps conversational Finance aligned with the web API and avoids
creating a second Telegram-only data path.

## OSS review and deliberate non-adoption

The implementation was checked against successful open-source products and
focused libraries:

- [Firefly III](https://github.com/firefly-iii/firefly-iii) validates the
  separation between recurring financial operations and currency-aware
  reporting.
- [Actual Budget](https://github.com/actualbudget/actual) is a useful
  local-first reference, while its documented lack of native multi-currency
  reinforces that FX is a separate product decision.
- [python-dateutil](https://github.com/dateutil/dateutil) and
  [rrule.js](https://github.com/jkbrzt/rrule) cover broad recurrence standards,
  but they are intentionally not added as dependencies: Mira currently needs
  three transparent rules and no iCalendar import/export.

This is a reference audit, not copied code. If Finance later needs arbitrary
RRULE input, exchange-rate history, or account reconciliation, it requires a
new proposal and a migration plan rather than silently expanding this model.

Actual Budget is retained as a reference for a possible future budget layer:
ledger history, budgets and accounts should remain separate concerns. No budget
or account entity is introduced by the current recurrence/currency slice; the
decision and license boundary are tracked in
[OSS_AUDIT_2026-08-04.md](../decisions/OSS_AUDIT_2026-08-04.md).

## Migration and tests

Migration `031_finance_currency_recurrence.sql` adds the currency and schedule
columns with backward-compatible defaults. Regression coverage is in
`backend/tests/test_finance_recurrence.py` and locks mixed-currency grouping,
weekly/monthly/yearly dates, month-end clamping, and forecast totals.
