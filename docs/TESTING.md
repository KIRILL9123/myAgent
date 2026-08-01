# Test infrastructure

## Running tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run the full automated suite
pytest

# Or explicitly:
python -m pytest backend/tests/

# Run with verbose output
pytest -v

# Run a specific test file
pytest backend/tests/test_safety_boundary.py -v
```

## What tests cover

### Automated (run with `pytest`)
- **Tool validation** — Pydantic model correctness, registry completeness, validation-before-permission
- **Dry-run safety** — All 27 write paths respect execution mode
- **Safety boundary** — Countdown, email sync-state, memory, recurring transactions, Telegram
- **Safety regression** — Execution mode, permissions, RED confirmation, API auth, side-effect suppression
- **Memory lifecycle** — Fact extraction, dedup, approval, graph, consolidation
- **Memory retrieval** — Keyword matching, stem matching, stopword filtering, LLM fallback
- **Confirmation logic** — RED action confirmation/cancellation matching, negation bypass
- **API endpoints** — Pending facts, approval, rejection, graph, authentication
- **Temporal memory** — valid_from/valid_to filtering, expired fact exclusion
- **Backup/restore** — Creation, integrity check, retention, restore

### Not in default suite
The following are interactive/manual tools and are NOT run by `pytest`:
- `dev-tools/restore_backup.py` — interactive backup restore (requires `EXECUTION_MODE=real`)
- `dev-tools/test_morning_summary.py` — trigger morning summary (requires `EXECUTION_MODE=real`)
- `dev-tools/test_caldav.py` — list CalDAV events (read-only)
- `dev-tools/test_mail.py` — test IMAP connection (requires `EXECUTION_MODE=real`)
- `dev-tools/test_gmail2.py` — test Gmail IMAP (requires `EXECUTION_MODE=real`)

## Test isolation

- **Database**: Every test uses an isolated temporary SQLite database via the `test_db` fixture
- **Execution mode**: Defaults to `DRY_RUN`. Tests opt into `REAL` mode via `real_mode` fixture
- **External services**: All external connectors (Ollama, IMAP, SMTP, CalDAV, Telegram) are mocked
- **LLM calls**: Mocked via `mock_llm` fixture (shared AsyncMock across all import locations)
- **API key**: Tests use a fixed test key; real credentials are never required

## CI

GitHub Actions runs the full suite on push and PR to main/master.
CI uses `EXECUTION_MODE=dry_run` — no external side effects possible.

## Adding tests

1. Use fixtures from `backend/tests/conftest.py`:
   - `test_db` — isolated SQLite
   - `real_mode` — enable writes (default is dry_run)
   - `mock_llm` — mock Ollama calls
   - `api_client` / `api_headers` — authenticated test client

2. Async tests: just use `async def` — pytest-asyncio auto mode handles it.

3. Mark slow/external tests with `@pytest.mark.slow` or `@pytest.mark.external`.
