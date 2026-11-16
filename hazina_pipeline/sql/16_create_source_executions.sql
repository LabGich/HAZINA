BEGIN;

CREATE TABLE ops.source_executions (
    source_execution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES ops.pipeline_runs(run_id)
        ON DELETE RESTRICT,

    source_id BIGINT NOT NULL
        REFERENCES ops.source_registry(source_id)
        ON DELETE RESTRICT,

    mapping_id TEXT,

    mapping_version VARCHAR(20),

    execution_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (
            execution_status IN (
                'PENDING',
                'RUNNING',
                'SUCCESS',
                'PARTIAL_SUCCESS',
                'FAILED',
                'SKIPPED',
                'CANCELLED'
            )
        ),

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    records_received INTEGER NOT NULL DEFAULT 0,
    records_loaded INTEGER NOT NULL DEFAULT 0,
    records_mapped INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    records_skipped INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,

    error_code VARCHAR(50),

    error_message TEXT,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT source_executions_mapping_pair_check
        CHECK (
            (mapping_id IS NULL AND mapping_version IS NULL)
            OR
            (mapping_id IS NOT NULL AND mapping_version IS NOT NULL)
        ),

    CONSTRAINT source_executions_metadata_check
        CHECK (jsonb_typeof(metadata) = 'object'),

    CONSTRAINT source_executions_counters_check
        CHECK (
            records_received >= 0
            AND records_loaded >= 0
            AND records_mapped >= 0
            AND records_rejected >= 0
            AND records_skipped >= 0
            AND records_updated >= 0
        ),

    CONSTRAINT source_executions_timestamps_check
        CHECK (
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT source_executions_run_source_unique
        UNIQUE (run_id, source_id)
);

CREATE INDEX idx_source_executions_run_id
    ON ops.source_executions (run_id);

CREATE INDEX idx_source_executions_source_id
    ON ops.source_executions (source_id);

CREATE INDEX idx_source_executions_status
    ON ops.source_executions (execution_status);

CREATE INDEX idx_source_executions_started_at
    ON ops.source_executions (started_at);

COMMIT;