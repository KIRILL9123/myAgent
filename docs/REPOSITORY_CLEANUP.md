# Repository Cleanup Candidates

Evidence-based candidates for later cleanup/consolidation. No production deletions were performed in this issue.

| Path | Reason | Evidence | Confidence | Recommended action |
|---|---|---|---|---|
| `frontend/README.md` | Default Vite template; does not describe actual app | Contains template text unrelated to current modules | High | consolidate (replace with project-specific frontend doc) |
| `backend/app/permissions/tool_permissions.json` (`create_reminder`, `bulk_delete`) | Permission entries without active tool implementation/dispatch | No tool schema/dispatch usage in `backend/app/agent/orchestrator.py` | High | deprecate |
| `dev-tools/test_mail.py` | Live external IMAP script; unsafe as “test” artifact | Direct login to IMAP with env credentials | High | deprecate |
| `dev-tools/test_caldav.py` | Live external CalDAV script; unsafe as “test” artifact | Direct connector call to real CalDAV | High | deprecate |
| `dev-tools/test_gmail.py` | Live external auth check | Calls `_connect("gmail")` directly | High | deprecate |
| `dev-tools/test_gmail2.py` | Live external mailbox read script | Calls `list_unread_emails` directly | High | deprecate |
| `dev-tools/test_gmail3.py` | Credential print/debug script | Prints credential presence values | Medium | delete |
| `dev-tools/test_summary.py` | Runs side-effecting scheduled summary pipeline | Calls `morning_summary()` (mail/calendar/telegram) | High | deprecate |
| `dev-tools/test_morning_summary.py` | Same side-effecting behavior as above | Calls `morning_summary()` | High | deprecate |
| `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg`, `frontend/src/assets/hero.png` | Likely unused template/static leftovers | No imports from `frontend/src` | Medium | delete |
| `frontend/src/App.css` | Placeholder stylesheet likely unused | Not imported by `App.tsx` | Medium | delete |
| `docs/ARCHITECTURE.md` | Contains stale architecture statements | Mentions vanilla frontend and Mem0 sublayer | High | consolidate |
| `docs/BACKLOG.md` | Some lines stale vs implemented roadmap | Voice and memory notes contradict current implementation | High | consolidate |
| `README.md` status section | Phase status outdated | Mentions “Phase 1 active” despite broader implemented modules | High | consolidate |
| `backend/tests/test_memory_flow.py` | Script-style integration test, not pytest test | Uses `asyncio.run(main())`, no pytest test functions | Medium | consolidate |

