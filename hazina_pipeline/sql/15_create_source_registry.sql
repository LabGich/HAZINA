BEGIN;

CREATE TABLE ops.source_registry (
    source_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source_name VARCHAR(50) NOT NULL UNIQUE,

    source_type VARCHAR(10) NOT NULL
        CHECK (source_type IN ('FILE', 'API')),

    source_identifier TEXT,

    description TEXT,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    supported_formats JSONB NOT NULL DEFAULT '[]'::JSONB
        CHECK (jsonb_typeof(supported_formats) = 'array'),

    default_mapping_id TEXT,

    default_mapping_version VARCHAR(20),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT source_registry_mapping_pair_check
        CHECK (
            (default_mapping_id IS NULL AND default_mapping_version IS NULL)
            OR
            (default_mapping_id IS NOT NULL AND default_mapping_version IS NOT NULL)
        )
);

CREATE INDEX idx_source_registry_enabled
    ON ops.source_registry (enabled);

CREATE INDEX idx_source_registry_source_type
    ON ops.source_registry (source_type);

COMMIT;