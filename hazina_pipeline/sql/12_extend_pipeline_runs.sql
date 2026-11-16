
-- =========================================================
-- HAZINA V2
-- Migration 12: Extend pipeline run tracking
-- =========================================================

BEGIN;

-- 1. API and multi-source runs do not require a filename.

ALTER TABLE ops.pipeline_runs
ALTER COLUMN source_file DROP NOT NULL;


-- 2. Add run classification and execution metadata.

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS run_type VARCHAR(20)
NOT NULL DEFAULT 'FILE';

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(30)
NOT NULL DEFAULT 'MANUAL';

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS records_skipped INTEGER
NOT NULL DEFAULT 0;

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS records_updated INTEGER
NOT NULL DEFAULT 0;

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS metadata JSONB
NOT NULL DEFAULT '{}'::JSONB;


-- 3. Restrict run types.

ALTER TABLE ops.pipeline_runs
ADD CONSTRAINT chk_pipeline_runs_run_type
CHECK (
    run_type IN ('FILE', 'API', 'MIXED', 'BACKFILL')
);


-- 4. Restrict pipeline run statuses.

ALTER TABLE ops.pipeline_runs
ADD CONSTRAINT chk_pipeline_runs_run_status
CHECK (
    run_status IN (
        'PENDING',
        'RUNNING',
        'SUCCESS',
        'PARTIAL_SUCCESS',
        'FAILED',
        'CANCELLED'
    )
);


-- 5. Protect counters from negative values.

ALTER TABLE ops.pipeline_runs
ADD CONSTRAINT chk_pipeline_runs_nonnegative_counters
CHECK (
    records_received >= 0
    AND records_loaded >= 0
    AND records_rejected >= 0
    AND records_duplicated >= 0
    AND records_unique_eligible >= 0
    AND records_promoted >= 0
    AND records_already_in_core >= 0
    AND records_skipped >= 0
    AND records_updated >= 0
);

COMMIT;
