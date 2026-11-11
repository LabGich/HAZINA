-- Associate each raw record with its pipeline execution.

ALTER TABLE raw.transactions
ADD COLUMN IF NOT EXISTS run_id BIGINT
REFERENCES ops.pipeline_runs(run_id);

-- Associate existing raw records with their original run.
UPDATE raw.transactions
SET run_id = 1
WHERE run_id IS NULL;
