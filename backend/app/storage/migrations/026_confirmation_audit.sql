ALTER TABLE pending_actions ADD COLUMN failure_reason TEXT;
ALTER TABLE pending_actions ADD COLUMN claimed_at DATETIME;
ALTER TABLE pending_actions ADD COLUMN resolved_at DATETIME;

CREATE INDEX IF NOT EXISTS idx_pending_actions_status_channel
    ON pending_actions(status, source_channel, chat_id);
