-- Add source record and pipeline run traceability to staging
ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS raw_id BIGINT
REFERENCES raw.transactions(raw_id);

ALTER TABLE staging.transactions
ADD COLUMN IF NOT EXISTS run_id BIGINT
REFERENCES ops.pipeline_runs(run_id);

-- Each raw record can produce atmost one staging record
CREATE UNIQUE INDEX IF NOT EXISTS
    idx_staging_transactions_raw_id
ON staging.transactions(raw_id);

-- Every staged record must have a source and pipeline run
ALTER TABLE staging.transactions
ALTER COLUMN raw_id SET NOT NULL;

ALTER TABLE staging.transactions
ALTER COLUMN run_id SET NOT NULL;