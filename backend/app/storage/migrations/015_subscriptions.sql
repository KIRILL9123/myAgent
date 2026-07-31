CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    provider TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'PROPOSED'
        CHECK (status IN ('PROPOSED', 'ACTIVE', 'CANCELLED', 'EXPIRED')),
    subscription_type TEXT NOT NULL DEFAULT 'UNKNOWN'
        CHECK (subscription_type IN ('TRIAL', 'PAID', 'UNKNOWN')),
    amount REAL,
    currency TEXT,
    billing_cycle TEXT,
    trial_ends_at TEXT,
    next_charge_at TEXT,
    reminder_at TEXT,
    reminder_sent_at TEXT,
    cancellation_url TEXT,
    cancellation_instructions TEXT,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    provenance_json TEXT NOT NULL DEFAULT '{}',
    source_type TEXT NOT NULL CHECK (source_type IN ('MANUAL', 'EMAIL')),
    source_ref TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    activated_at TEXT,
    cancelled_at TEXT,
    expired_at TEXT,
    approval_provenance_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status_charge
    ON subscriptions(status, next_charge_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status_reminder
    ON subscriptions(status, reminder_at, reminder_sent_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_source_ref
    ON subscriptions(source_ref);

CREATE TABLE IF NOT EXISTS subscription_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id TEXT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subscription_events_subscription
    ON subscription_events(subscription_id, created_at);
