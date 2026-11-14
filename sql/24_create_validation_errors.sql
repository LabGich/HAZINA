CREATE TABLE ops.validation_errors (
    validation_error_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES ops.pipeline_runs(run_id) ON DELETE RESTRICT,

    source_execution_id BIGINT NOT NULL
        REFERENCES ops.source_executions(source_execution_id)
        ON DELETE RESTRICT,

    staging_id BIGINT NOT NULL
        REFERENCES staging.transactions(staging_id) ON DELETE RESTRICT,

    raw_id BIGINT NOT NULL
        REFERENCES raw.transactions(raw_id) ON DELETE RESTRICT,

    transaction_id TEXT NOT NULL,

    error_code VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    field_name TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validation_errors_execution
    ON ops.validation_errors(source_execution_id);

CREATE INDEX idx_validation_errors_staging
    ON ops.validation_errors(staging_id);

CREATE INDEX idx_validation_errors_run
    ON ops.validation_errors(run_id);