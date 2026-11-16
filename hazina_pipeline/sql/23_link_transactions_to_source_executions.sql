-- =========================================================
-- HAZINA V2
-- Migration 23: Link transactions to source executions
-- =========================================================

BEGIN;

-- Link raw records to their source execution.
ALTER TABLE raw.transactions
ADD COLUMN source_execution_id BIGINT;

ALTER TABLE raw.transactions
ADD CONSTRAINT raw_transactions_source_execution_fkey
FOREIGN KEY (source_execution_id)
REFERENCES ops.source_executions(source_execution_id)
ON DELETE RESTRICT;


-- Link staged records to their source execution.
ALTER TABLE staging.transactions
ADD COLUMN source_execution_id BIGINT;

ALTER TABLE staging.transactions
ADD CONSTRAINT staging_transactions_source_execution_fkey
FOREIGN KEY (source_execution_id)
REFERENCES ops.source_executions(source_execution_id)
ON DELETE RESTRICT;


-- Support execution-level queries.
CREATE INDEX idx_raw_transactions_source_execution
ON raw.transactions(source_execution_id);

CREATE INDEX idx_staging_transactions_source_execution
ON staging.transactions(source_execution_id);

COMMIT;