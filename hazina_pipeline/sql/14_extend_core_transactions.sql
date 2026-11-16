
BEGIN;

-- Allow transactions without a customer identifier.
ALTER TABLE core.transactions
    ALTER COLUMN customer_id DROP NOT NULL;

-- Add fields required by the V2 canonical transaction model.
ALTER TABLE core.transactions
    ADD COLUMN direction VARCHAR(10) NOT NULL DEFAULT 'UNKNOWN',
    ADD COLUMN description TEXT,
    ADD COLUMN counterparty TEXT,
    ADD COLUMN fee_amount NUMERIC(20,2),
    ADD COLUMN account_balance NUMERIC(20,2),
    ADD COLUMN updated_at TIMESTAMPTZ;

-- Restrict direction to supported values.
ALTER TABLE core.transactions
    ADD CONSTRAINT transactions_direction_check
    CHECK (direction IN ('DEBIT', 'CREDIT', 'UNKNOWN'));

-- Preserve the historical creation timestamp for existing records.
UPDATE core.transactions
SET updated_at = created_at;

-- Set defaults and enforce the timestamp requirement for future records.
ALTER TABLE core.transactions
    ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN updated_at SET NOT NULL;

COMMIT;
