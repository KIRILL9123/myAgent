CREATE TABLE IF NOT EXISTS pending_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    action_name TEXT NOT NULL,
    args TEXT,
    status TEXT DEFAULT 'pending',
    nonce_hash TEXT NOT NULL DEFAULT '',
    source_channel TEXT DEFAULT 'web',
    chat_id TEXT,
    telegram_message_id INTEGER,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_actions_session_id ON pending_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_pending_nonce_hash ON pending_actions(nonce_hash);
