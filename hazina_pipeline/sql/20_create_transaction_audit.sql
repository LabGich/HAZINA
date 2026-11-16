BEGIN;

CREATE TABLE ops.transaction_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id VARCHAR(50) NOT NULL
        REFERENCES core.transactions(transaction_id)
        ON DELETE RESTRICT,

    source_id BIGINT
        REFERENCES ops.source_registry(source_id)
        ON DELETE RESTRICT,

    source_execution_id BIGINT
        REFERENCES ops.source_executions(source_execution_id)
        ON DELETE RESTRICT,

    run_id BIGINT
        REFERENCES ops.pipeline_runs(run_id)
        ON DELETE RESTRICT,

    raw_id BIGINT
        REFERENCES raw.transactions(raw_id)
        ON DELETE RESTRICT,

    action_type VARCHAR(30) NOT NULL
        CHECK (
            action_type IN (
                'INSERT',
                'UPDATE',
                'MANUAL_CORRECTION',
                'IDENTITY_REVIEW'
            )
        ),

    previous_values JSONB NOT NULL DEFAULT '{}'::JSONB,

    new_values JSONB NOT NULL DEFAULT '{}'::JSONB,

    changed_fields JSONB NOT NULL DEFAULT '[]'::JSONB,

    mapping_id TEXT,

    mapping_version VARCHAR(20),

    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    changed_by TEXT,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT transaction_audit_previous_values_check
        CHECK (jsonb_typeof(previous_values) = 'object'),

    CONSTRAINT transaction_audit_new_values_check
        CHECK (jsonb_typeof(new_values) = 'object'),

    CONSTRAINT transaction_audit_changed_fields_check
        CHECK (jsonb_typeof(changed_fields) = 'array'),

    CONSTRAINT transaction_audit_metadata_check
        CHECK (jsonb_typeof(metadata) = 'object'),

    CONSTRAINT transaction_audit_mapping_pair_check
        CHECK (
            (mapping_id IS NULL AND mapping_version IS NULL)
            OR
            (mapping_id IS NOT NULL AND mapping_version IS NOT NULL)
        )
);

CREATE INDEX idx_transaction_audit_transaction_id
    ON ops.transaction_audit (transaction_id);

CREATE INDEX idx_transaction_audit_run_id
    ON ops.transaction_audit (run_id);

CREATE INDEX idx_transaction_audit_source_id
    ON ops.transaction_audit (source_id);

CREATE INDEX idx_transaction_audit_changed_at
    ON ops.transaction_audit (changed_at DESC);

CREATE INDEX idx_transaction_audit_action_type
    ON ops.transaction_audit (action_type);


-- Prevent ordinary modification or deletion of audit history.

CREATE OR REPLACE FUNCTION ops.reject_transaction_audit_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Transaction audit records are append-only. UPDATE and DELETE are not permitted.';
END;
$$;

CREATE TRIGGER trg_transaction_audit_append_only
BEFORE UPDATE OR DELETE
ON ops.transaction_audit
FOR EACH ROW
EXECUTE FUNCTION ops.reject_transaction_audit_mutation();

COMMIT;