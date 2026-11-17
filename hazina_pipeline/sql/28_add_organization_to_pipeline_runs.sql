
-- =========================================================
-- HAZINA MULTI-TENANT PIPELINE RUN OWNERSHIP
-- Migration 28: Add organization ownership to pipeline runs
-- =========================================================

ALTER TABLE ops.pipeline_runs
ADD COLUMN IF NOT EXISTS organization_id BIGINT
    REFERENCES auth.organizations(organization_id)
    ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_organization
    ON ops.pipeline_runs(organization_id);
