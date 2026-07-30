CREATE TABLE IF NOT EXISTS mail_sync_state (
    account TEXT PRIMARY KEY,
    last_seen_uid INTEGER NOT NULL
);
