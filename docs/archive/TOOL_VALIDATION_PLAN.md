# Tool Validation Plan

## Current architecture (observed)
- Tool schemas for LLM are defined inline in `backend/app/agent/orchestrator.py` (`AVAILABLE_TOOLS`).
- Arguments are parsed dynamically in `execute_tool()` (`json.loads` if string).
- Dispatch is performed via `_dispatch_tool()` conditional chain.
- Permission check happens before execution (`check_permission`).
- Audit logging uses `log_action()` around permission and execution phases.

## Target execution pipeline
`Tool schema -> Pydantic validation -> Permission check -> Dry-run/real execution -> Audit`

## Migration plan (no refactor yet)
1. **Introduce per-tool Pydantic models** colocated in a new module (e.g., `backend/app/agent/tool_models.py`).
2. **Map tool name -> model** (small registry dictionary first).
3. In `execute_tool()`, parse raw args then validate with model.
4. On validation failure, return structured `status=error` with model errors.
5. Keep current permission checker unchanged.
6. Add execution-mode hook (future dry-run architecture).
7. Standardize all tool return contracts (`status/message/...`) before deeper registry work.

## Tools needing validation models first
- Calendar: `list_events`, `search_events`, `create_event`, `modify_event`, `delete_event`
- Mail: `list_unread_emails`, `search_emails`, `send_email`
- Finance: `add_transaction`, `get_transactions`, `get_summary`
- Countdown: `add_countdown`, `get_all_countdowns`, `delete_countdown`

## Centralized Tool Registry evaluation
A centralized registry is recommended eventually for:
- schema, model, permission level, executor, audit metadata in one place
- reduced duplication between `AVAILABLE_TOOLS`, dispatch, and permission docs

Not recommended in this issue: full registry refactor (too broad for current scope).
