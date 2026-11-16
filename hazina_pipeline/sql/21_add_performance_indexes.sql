BEGIN;

-- Raw transaction lookups by pipeline run.
CREATE INDEX IF NOT EXISTS idx_raw_transactions_run_id
    ON raw.transactions (run_id);

-- Source-aware transaction lookups.
CREATE INDEX IF NOT EXISTS idx_raw_transactions_source_identity
    ON raw.transactions (
        source_name,
        source_account_id,
        source_transaction_id
    )
    WHERE source_transaction_id IS NOT NULL;

-- Raw ingestion-time queries.
CREATE INDEX IF NOT EXISTS idx_raw_transactions_ingested_at
    ON raw.transactions (ingested_at DESC);

-- Staging queries by run and deduplication outcome.
CREATE INDEX IF NOT EXISTS idx_staging_transactions_run_dedup
    ON staging.transactions (run_id, deduplication_status);

-- Date-based canonical transaction analytics.
CREATE INDEX IF NOT EXISTS idx_core_transactions_transaction_date
    ON core.transactions (transaction_date);

-- Pipeline error retrieval.
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_run_id
    ON ops.pipeline_errors (run_id);

COMMIT;