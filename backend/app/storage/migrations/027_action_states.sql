CREATE TABLE IF NOT EXISTS action_states (
    action_id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN ('read', 'snoozed', 'dismissed')),
    snoozed_until TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_action_states_state_until
    ON action_states(state, snoozed_until);
