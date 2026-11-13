BEGIN;

CREATE TABLE ops.mapping_errors (
    error_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES ops.pipeline_runs(run_id)
        ON DELETE RESTRICT,

    source_execution_id BIGINT
        REFERENCES ops.source_executions(source_execution_id)
        ON DELETE RESTRICT,

    raw_id BIGINT
        REFERENCES raw.transactions(raw_id)
        ON DELETE RESTRICT,

    mapping_id TEXT,

    mapping_version VARCHAR(20),

    error_code VARCHAR(50) NOT NULL,

    error_message TEXT NOT NULL,

    field_name TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    resolved_at TIMESTAMPTZ,

    resolution_notes TEXT,

    CONSTRAINT mapping_errors_mapping_pair_check
        CHECK (
            (mapping_id IS NULL AND mapping_version IS NULL)
            OR
            (mapping_id IS NOT NULL AND mapping_version IS NOT NULL)
        ),

    CONSTRAINT mapping_errors_resolution_check
        CHECK (
            resolved_at IS NULL
            OR resolved_at >= created_at
        )
);

CREATE INDEX idx_mapping_errors_run_id
    ON ops.mapping_errors (run_id);

CREATE INDEX idx_mapping_errors_source_execution
    ON ops.mapping_errors (source_execution_id);

CREATE INDEX idx_mapping_errors_raw_id
    ON ops.mapping_errors (raw_id);

CREATE INDEX idx_mapping_errors_error_code
    ON ops.mapping_errors (error_code);

CREATE INDEX idx_mapping_errors_unresolved
    ON ops.mapping_errors (created_at)
    WHERE resolved_at IS NULL;

COMMIT;