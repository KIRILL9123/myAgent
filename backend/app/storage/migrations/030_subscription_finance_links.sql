ALTER TABLE recurring_templates ADD COLUMN active INTEGER NOT NULL DEFAULT 1;
ALTER TABLE transactions ADD COLUMN source_template_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_transactions_source_template
    ON transactions(source_template_id, date);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_source_template_date
    ON transactions(source_template_id, date)
    WHERE source_template_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS subscription_finance_links (
    id TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL UNIQUE REFERENCES subscriptions(id) ON DELETE CASCADE,
    recurring_template_id INTEGER UNIQUE REFERENCES recurring_templates(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK (status IN ('PROPOSED', 'LINKED', 'DECLINED', 'UNLINKED')),
    approval_id TEXT,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    linked_at TEXT,
    unlinked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_subscription_finance_links_status
    ON subscription_finance_links(status, updated_at);

DROP INDEX IF EXISTS idx_approval_requests_status_created;

ALTER TABLE approval_requests RENAME TO approval_requests_legacy;

CREATE TABLE approval_requests (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('FACT', 'COMMITMENT', 'SUBSCRIPTION', 'ACTION', 'SANDBOX_APPLY', 'SKILL', 'DOCUMENT_PROPOSAL', 'SUBSCRIPTION_FINANCE_LINK')),
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    source_channel TEXT NOT NULL DEFAULT 'web',
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'FAILED')),
    resolution_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    UNIQUE(kind, source_id)
);

INSERT INTO approval_requests
    (id, kind, source_id, title, summary, payload_json, source_channel, status,
     resolution_note, created_at, updated_at, resolved_at)
SELECT id, kind, source_id, title, summary, payload_json, source_channel, status,
       resolution_note, created_at, updated_at, resolved_at
FROM approval_requests_legacy;

DROP TABLE approval_requests_legacy;

CREATE INDEX IF NOT EXISTS idx_approval_requests_status_created
    ON approval_requests(status, created_at);
