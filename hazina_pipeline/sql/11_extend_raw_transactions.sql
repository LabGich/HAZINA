
-- =========================================================
-- HAZINA V2
-- Migration 11: Extend raw transaction storage
-- =========================================================

BEGIN;

-- 1. Add V2 source and payload metadata.

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS raw_payload JSONB;

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS source_name TEXT;

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS source_type TEXT;

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS source_transaction_id TEXT;

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS source_account_id TEXT;

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS source_reference TEXT;

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS source_metadata JSONB
NOT NULL DEFAULT '{}'::JSONB;


-- 2. Backfill historical V1 records.
-- Preserve the original values as text inside JSONB.

UPDATE raw.transactions
SET
    raw_payload = jsonb_build_object(
        'transaction_id', transaction_id,
        'customer_id', customer_id,
        'transaction_date', transaction_date,
        'transaction_type', transaction_type,
        'amount', amount,
        'currency', currency,
        'payment_method', payment_method,
        'status', status
    ),
    source_type = 'FILE',
    source_metadata = source_metadata ||
        CASE
            WHEN source_file IS NOT NULL
            THEN jsonb_build_object('legacy_source_file', source_file)
            ELSE '{}'::JSONB
        END
WHERE raw_payload IS NULL;


-- 3. Enforce required raw payload and source type.

ALTER TABLE raw.transactions
ALTER COLUMN raw_payload SET NOT NULL;

ALTER TABLE raw.transactions
ALTER COLUMN source_type SET NOT NULL;

ALTER TABLE raw.transactions
ADD CONSTRAINT chk_raw_source_type
CHECK (source_type IN ('FILE', 'API'));


-- 4. Allow API records without a source filename.

ALTER TABLE raw.transactions
ALTER COLUMN source_file DROP NOT NULL;

COMMIT;
