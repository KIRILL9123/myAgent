# Permission System

The Home Agent operates on a strict, hardcoded whitelist permission system to ensure safety and prevent the LLM from making unauthorized destructive actions.

The permission logic is located in `backend/app/permissions/permission_checker.py` and is driven by `tool_permissions.json`.

## Levels

- **Green**: Safe, read-only actions (e.g., `list_events`, `search_events`, `list_emails`). The agent can execute these freely.
- **Yellow**: State-altering but generally safe actions (e.g., `create_event`, `create_reminder`). The agent can execute these, but they might trigger a notification or require secondary validation depending on future configuration.
- **Red**: Destructive or high-impact actions (e.g., `delete_event`, `modify_event`, `bulk_delete`). These require explicit human approval before the orchestrator will execute the tool call.

*Note: In Phase 1, only Green actions are implemented.*
