# Testing Gaps (Risk Prioritized)

## Highest priority (side-effect prevention)
1. **RED action confirmation flow**
   - Need tests that verify red tools are never executed without explicit confirm.
2. **SMTP send protection**
   - Need tests proving no real email can be sent in test/CI mode.
3. **Calendar mutation protection**
   - Need tests proving create/modify/delete are blocked or dry-run in non-production modes.
4. **Telegram outbound/inbound isolation**
   - Need tests for notifier/listener with fake transport only.
5. **Scheduler safety**
   - Need tests asserting scheduled jobs do not execute real side effects in CI/sandbox.

## High priority (security/integrity)
6. **Tool permission matrix tests**
   - Verify each tool’s permission level and behavior on unknown actions.
7. **Prompt injection handling tests**
   - Validate wrapping and safe handling of external content.
8. **Memory approval and contradiction tests**
   - Validate pending/approved/rejected/merged transitions and contradiction edges.

## Medium priority (domain mutation correctness)
9. **Finance mutation tests**
   - Add/delete/recurring behavior and duplicate safeguards.
10. **API auth boundary tests**
   - Ensure `/api/*` key checks behave consistently.

## Current baseline
- Existing backend tests mostly cover memory flow: `backend/tests/test_api_endpoints.py`.
- No strong side-effect isolation tests exist yet for mail/calendar/telegram/scheduler.
