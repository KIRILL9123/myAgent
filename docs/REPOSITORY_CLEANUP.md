# Repository Cleanup Candidates

> **Responsibility**: Evidence-based cleanup candidates only. No production deletions are performed here.  
> Each candidate was verified against the actual repository state.

| Path | Reason | Evidence | Confidence | Recommended action |
|---|---|---|---|---|
| `frontend/README.md` | Default Vite template; does not describe actual app | Contains template text unrelated to current modules | High | Replace with project-specific frontend doc |
| `backend/app/permissions/tool_permissions.json` (`create_reminder`, `bulk_delete` entries) | Permission entries without active tool implementation or dispatch | Neither `create_reminder` nor `bulk_delete` appears in `backend/app/agent/orchestrator.py` (verified via grep) | High | Deprecate / remove entries |
| `dev-tools/test_mail.py` | Live external IMAP script; unsafe as a "test" artifact | Direct login to IMAP with env credentials | High | Deprecate (add dry-run guard or remove) |
| `dev-tools/test_caldav.py` | Live external CalDAV script; unsafe as a "test" artifact | Direct connector call to real CalDAV | High | Deprecate (add dry-run guard or remove) |
| `dev-tools/test_gmail.py` | Live external auth check | Calls `_connect("gmail")` directly | High | Deprecate (add dry-run guard or remove) |
| `dev-tools/test_gmail2.py` | Live external mailbox read script | Calls `list_unread_emails` directly | High | Deprecate (add dry-run guard or remove) |
| `dev-tools/test_gmail3.py` | Credential print/debug script | Prints credential presence values | Medium | Delete |
| `dev-tools/test_summary.py` | Runs side-effecting scheduled summary pipeline | Calls `morning_summary()` (mail/calendar/Telegram) | High | Deprecate (add dry-run guard or remove) |
| `dev-tools/test_morning_summary.py` | Same side-effecting behavior as above | Calls `morning_summary()` | High | Deprecate (add dry-run guard or remove) |
| `frontend/src/assets/react.svg` | Unused Vite template asset | No import found in `frontend/src/` (verified via grep) | Medium | Delete |
| `frontend/src/assets/vite.svg` | Unused Vite template asset | No import found in `frontend/src/` (verified via grep) | Medium | Delete |
| `frontend/src/assets/hero.png` | Unused static asset | No import found in `frontend/src/` (verified via grep) | Medium | Delete |
| `frontend/src/App.css` | Effectively empty placeholder | File content is `/* App.css cleared for Tailwind */`; not imported by `App.tsx` (verified via grep) | Medium | Delete |
| `docs/ARCHITECTURE.md` | Partially historical | Top-level note acknowledges historical content; body has been updated (Mem0 removed, stack is accurate). Consolidate with ARCHITECTURE_STATUS.md or update remaining stale wording. | Low | Minor consolidation or leave with existing note |
| `backend/tests/test_memory_flow.py` | Script-style integration test, not a pytest test | Uses `asyncio.run(main())` with no pytest test functions; not discovered by pytest runner | Medium | Refactor into proper pytest tests or document as a manual dev script |

## Notes on dev-tools safety

All scripts in `dev-tools/` that connect to real external services (`test_mail.py`, `test_caldav.py`, `test_gmail.py`, `test_gmail2.py`, `test_summary.py`, `test_morning_summary.py`) share the same safety problem: they execute real network side effects if credentials are present in the environment. The preferred remediation is the dry-run architecture defined in [DRY_RUN_ARCHITECTURE.md](DRY_RUN_ARCHITECTURE.md). Until dry-run mode exists, these scripts should not be run in any automated or CI context.
