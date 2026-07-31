CREATE TABLE IF NOT EXISTS notification_preferences (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 1,
    timezone TEXT NOT NULL DEFAULT 'Europe/Berlin',
    quiet_hours_start TEXT NOT NULL DEFAULT '22:00',
    quiet_hours_end TEXT NOT NULL DEFAULT '08:00',
    max_messages_per_window INTEGER NOT NULL DEFAULT 3,
    window_minutes INTEGER NOT NULL DEFAULT 60,
    min_priority TEXT NOT NULL DEFAULT 'medium',
    coalesce_window_minutes INTEGER NOT NULL DEFAULT 15,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO notification_preferences (id) VALUES (1);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    action_ids_json TEXT NOT NULL DEFAULT '[]',
    priority TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('sent', 'suppressed', 'failed', 'dry_run')),
    reason TEXT,
    sent_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_notification_deliveries_dedupe
    ON notification_deliveries(channel, recipient, dedupe_key, status, sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_window
    ON notification_deliveries(channel, recipient, status, sent_at);
