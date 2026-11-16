-- Give @ record  a place to store its classification
-- Lets us identify what happened w/o modifying or deleting raw data
-- We'll add two columns:
-- - deduplication_status: records whether the transaction is unique, an exact duplicate, or conflicting
-- - duplicate_of_raw_id: identifies the retained raw record when an exact duplicate is found
-- The retained copy of an exact duplicate pair will be classified as UNIQUE
-- the redundant copy will be EXACT_DUPLICATE
-- both versions of a conflict will be CONFLICTING_DUPLICATE

-- Add deduplication classification to staged transactions.

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS deduplication_status VARCHAR(30)
NOT NULL DEFAULT 'PENDING';

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS duplicate_of_raw_id BIGINT
REFERENCES raw.transactions(raw_id);

-- Restrict deduplication classifications.
ALTER TABLE staging.transactions
ADD CONSTRAINT chk_deduplication_status
CHECK (
    deduplication_status IN (
        'PENDING',
        'UNIQUE',
        'EXACT_DUPLICATE',
        'CONFLICTING_DUPLICATE'
    )
);
