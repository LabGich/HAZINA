BEGIN;

CREATE TABLE ops.ingestion_checkpoints (
    checkpoint_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source_id BIGINT NOT NULL
        REFERENCES ops.source_registry(source_id)
        ON DELETE RESTRICT,

    source_execution_id BIGINT
        REFERENCES ops.source_executions(source_execution_id)
        ON DELETE RESTRICT,

    checkpoint_name VARCHAR(100) NOT NULL,

    checkpoint_type VARCHAR(30) NOT NULL
        CHECK (
            checkpoint_type IN (
                'API_CURSOR',
                'SYNC_TOKEN',
                'DATE_RANGE',
                'PAGE',
                'BATCH',
                'WEBHOOK_EVENT'
            )
        ),

    checkpoint_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (
            checkpoint_status IN (
                'PENDING',
                'IN_PROGRESS',
                'COMPLETED',
                'FAILED'
            )
        ),

    checkpoint_data JSONB NOT NULL DEFAULT '{}'::JSONB,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT ingestion_checkpoints_data_check
        CHECK (jsonb_typeof(checkpoint_data) = 'object'),

    CONSTRAINT ingestion_checkpoints_metadata_check
        CHECK (jsonb_typeof(metadata) = 'object'),

    CONSTRAINT ingestion_checkpoints_timestamps_check
        CHECK (
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
        )
);

CREATE INDEX idx_ingestion_checkpoints_source_name
    ON ops.ingestion_checkpoints (
        source_id,
        checkpoint_name,
        created_at DESC
    );

CREATE INDEX idx_ingestion_checkpoints_execution
    ON ops.ingestion_checkpoints (source_execution_id);

CREATE INDEX idx_ingestion_checkpoints_status
    ON ops.ingestion_checkpoints (checkpoint_status);

CREATE INDEX idx_ingestion_checkpoints_created_at
    ON ops.ingestion_checkpoints (created_at);

COMMIT;