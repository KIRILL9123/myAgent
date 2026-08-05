CREATE TABLE IF NOT EXISTS calendar_events (
    uid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    start_datetime TEXT NOT NULL,
    end_datetime TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_range
    ON calendar_events (start_datetime, end_datetime);
