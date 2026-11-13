
-- =========================================================
-- HAZINA V2
-- Migration 13: Extend staging transactions
-- =========================================================

BEGIN;

-- 1. Make customer identity optional.
-- Existing V1 customer IDs remain unchanged.

ALTER TABLE staging.transactions
ALTER COLUMN customer_id DROP NOT NULL;


-- 2. Add source identity fields.

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS source_name TEXT;

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS source_transaction_id TEXT;

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS source_account_id TEXT;


-- 3. Add canonical transaction fields.

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS direction VARCHAR(10)
NOT NULL DEFAULT 'UNKNOWN';

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS counterparty TEXT;

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS fee_amount NUMERIC(20,2);

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS account_balance NUMERIC(20,2);


-- 4. Add mapping traceability.

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS mapping_id TEXT;

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS mapping_version TEXT;


-- 5. Preserve source-specific metadata.

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS source_metadata JSONB
NOT NULL DEFAULT '{}'::JSONB;


-- 6. Restrict transaction direction.

ALTER TABLE staging.transactions
ADD CONSTRAINT chk_staging_direction
CHECK (
    direction IN ('DEBIT', 'CREDIT', 'UNKNOWN')
);

COMMIT;
