BEGIN;

CREATE TABLE ops.source_transaction_identity (
    identity_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source_id BIGINT NOT NULL
        REFERENCES ops.source_registry(source_id)
        ON DELETE RESTRICT,

    source_account_id TEXT,

    source_transaction_id TEXT NOT NULL,

    transaction_id VARCHAR(50) NOT NULL
        REFERENCES core.transactions(transaction_id)
        ON DELETE RESTRICT,

    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT source_identity_external_id_check
        CHECK (length(trim(source_transaction_id)) > 0),

    CONSTRAINT source_identity_metadata_check
        CHECK (jsonb_typeof(metadata) = 'object'),

    CONSTRAINT source_identity_timestamps_check
        CHECK (last_seen_at >= first_seen_at)
);

CREATE UNIQUE INDEX uq_source_identity_with_account
    ON ops.source_transaction_identity (
        source_id,
        source_account_id,
        source_transaction_id
    )
    WHERE source_account_id IS NOT NULL;

CREATE UNIQUE INDEX uq_source_identity_without_account
    ON ops.source_transaction_identity (
        source_id,
        source_transaction_id
    )
    WHERE source_account_id IS NULL;

CREATE INDEX idx_source_identity_transaction_id
    ON ops.source_transaction_identity (transaction_id);

CREATE INDEX idx_source_identity_source_id
    ON ops.source_transaction_identity (source_id);

CREATE INDEX idx_source_identity_active
    ON ops.source_transaction_identity (is_active);

COMMIT;