ALTER TABLE calendar_events ADD COLUMN all_day INTEGER NOT NULL DEFAULT 0;
ALTER TABLE calendar_events ADD COLUMN recurrence TEXT;
ALTER TABLE calendar_events ADD COLUMN recurrence_until TEXT;
ALTER TABLE calendar_events ADD COLUMN reminder_minutes INTEGER;
