ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS records_unique_eligible INTEGER
NOT NULL DEFAULT 0;

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS records_promoted INTEGER
NOT NULL DEFAULT 0;

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS records_already_in_core INTEGER
NOT NULL DEFAULT 0;