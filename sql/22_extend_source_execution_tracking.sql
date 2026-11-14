-- =========================================================
-- HAZINA V2
-- Migration 22: Extend source execution tracking
-- =========================================================

BEGIN;

-- Allow multiple files from the same source in one run.
ALTER TABLE ops.source_executions
DROP CONSTRAINT source_executions_run_source_unique;


-- Add execution-level deduplication and promotion metrics.
ALTER TABLE ops.source_executions
ADD COLUMN records_duplicated INTEGER NOT NULL DEFAULT 0;

ALTER TABLE ops.source_executions
ADD COLUMN records_unique_eligible INTEGER NOT NULL DEFAULT 0;

ALTER TABLE ops.source_executions
ADD COLUMN records_promoted INTEGER NOT NULL DEFAULT 0;

ALTER TABLE ops.source_executions
ADD COLUMN records_already_in_core INTEGER NOT NULL DEFAULT 0;


-- Protect the new counters from negative values.
ALTER TABLE ops.source_executions
ADD CONSTRAINT source_executions_promotion_counters_check
CHECK (
    records_duplicated >= 0
    AND records_unique_eligible >= 0
    AND records_promoted >= 0
    AND records_already_in_core >= 0
);

COMMIT;