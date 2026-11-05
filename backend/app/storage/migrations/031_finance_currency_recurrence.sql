ALTER TABLE transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'EUR';
ALTER TABLE recurring_templates ADD COLUMN currency TEXT NOT NULL DEFAULT 'EUR';
ALTER TABLE recurring_templates ADD COLUMN frequency TEXT NOT NULL DEFAULT 'monthly';
ALTER TABLE recurring_templates ADD COLUMN day_of_week INTEGER;
ALTER TABLE recurring_templates ADD COLUMN month_of_year INTEGER;

CREATE INDEX IF NOT EXISTS idx_recurring_templates_frequency
    ON recurring_templates(active, frequency, currency);
