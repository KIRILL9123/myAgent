ALTER TABLE transactions ADD COLUMN recurring_template_id INTEGER REFERENCES recurring_templates(id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_recurring_template_month
ON transactions (recurring_template_id, substr(date, 1, 7))
WHERE recurring_template_id IS NOT NULL;
