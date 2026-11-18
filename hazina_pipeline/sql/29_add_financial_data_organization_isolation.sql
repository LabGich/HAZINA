-- 1. Historical data: existing raw, staging, core, identity, and audit records remain unassigned (organization_id IS NULL)
-- -- No ownership is inferred from historical runs
-- New V2 records: the application must explicitly populate organization IDs
-- -- The raw/staging composite foreign keys will reject mismatched non-null organization IDs
-- The migration deliberately does not add organization IDs to source_executions, mapping_errors, or validation_errors
-- -- their ownership is inherited through the pipeline run

BEGIN;

-- ============================================================
-- 1. Add organization ownership columns
-- Historical records intentionally remain NULL.
-- ============================================================

ALTER TABLE raw.transactions
    ADD COLUMN organization_id BIGINT;

ALTER TABLE staging.transactions
    ADD COLUMN organization_id BIGINT;

ALTER TABLE core.transactions
    ADD COLUMN organization_id BIGINT;

ALTER TABLE ops.source_transaction_identity
    ADD COLUMN organization_id BIGINT;

ALTER TABLE ops.transaction_audit
    ADD COLUMN organization_id BIGINT;


-- ============================================================
-- 2. Add organization foreign keys
-- ============================================================

ALTER TABLE raw.transactions
    ADD CONSTRAINT raw_transactions_organization_id_fkey
    FOREIGN KEY (organization_id)
    REFERENCES auth.organizations (organization_id)
    ON DELETE RESTRICT;

ALTER TABLE staging.transactions
    ADD CONSTRAINT staging_transactions_organization_id_fkey
    FOREIGN KEY (organization_id)
    REFERENCES auth.organizations (organization_id)
    ON DELETE RESTRICT;

ALTER TABLE core.transactions
    ADD CONSTRAINT core_transactions_organization_id_fkey
    FOREIGN KEY (organization_id)
    REFERENCES auth.organizations (organization_id)
    ON DELETE RESTRICT;

ALTER TABLE ops.source_transaction_identity
    ADD CONSTRAINT source_identity_organization_id_fkey
    FOREIGN KEY (organization_id)
    REFERENCES auth.organizations (organization_id)
    ON DELETE RESTRICT;

ALTER TABLE ops.transaction_audit
    ADD CONSTRAINT transaction_audit_organization_id_fkey
    FOREIGN KEY (organization_id)
    REFERENCES auth.organizations (organization_id)
    ON DELETE RESTRICT;


-- ============================================================
-- 3. Enforce raw/staging ownership against pipeline runs
-- ============================================================

ALTER TABLE ops.pipeline_runs
    ADD CONSTRAINT uq_pipeline_runs_run_organization
    UNIQUE (run_id, organization_id);

ALTER TABLE raw.transactions
    ADD CONSTRAINT raw_transactions_run_organization_fkey
    FOREIGN KEY (run_id, organization_id)
    REFERENCES ops.pipeline_runs (run_id, organization_id)
    MATCH SIMPLE
    ON DELETE RESTRICT;

ALTER TABLE staging.transactions
    ADD CONSTRAINT staging_transactions_run_organization_fkey
    FOREIGN KEY (run_id, organization_id)
    REFERENCES ops.pipeline_runs (run_id, organization_id)
    MATCH SIMPLE
    ON DELETE RESTRICT;



-- ============================================================
-- 4. Introduce core surrogate primary key
-- Explicitly populate existing rows before making it the PK.
-- ============================================================

ALTER TABLE core.transactions
    ADD COLUMN core_transaction_id BIGINT;

CREATE SEQUENCE core.transactions_core_transaction_id_seq;

ALTER TABLE core.transactions
    ALTER COLUMN core_transaction_id
    SET DEFAULT nextval('core.transactions_core_transaction_id_seq');

UPDATE core.transactions
SET core_transaction_id = nextval('core.transactions_core_transaction_id_seq')
WHERE core_transaction_id IS NULL;

ALTER TABLE core.transactions
    ALTER COLUMN core_transaction_id SET NOT NULL;

ALTER SEQUENCE core.transactions_core_transaction_id_seq
    OWNED BY core.transactions.core_transaction_id;

ALTER TABLE ops.source_transaction_identity
    DROP CONSTRAINT source_transaction_identity_transaction_id_fkey;

ALTER TABLE ops.transaction_audit
    DROP CONSTRAINT transaction_audit_transaction_id_fkey;

ALTER TABLE core.transactions
    DROP CONSTRAINT transactions_pkey;

ALTER TABLE core.transactions
    ADD CONSTRAINT core_transactions_pkey
    PRIMARY KEY (core_transaction_id);

-- Keep the business transaction ID unique within an organization.
ALTER TABLE core.transactions
    ADD CONSTRAINT uq_core_transactions_organization_transaction
    UNIQUE (organization_id, transaction_id);


-- ============================================================
-- 5. Replace source identity foreign key with composite FK
-- ============================================================

ALTER TABLE ops.source_transaction_identity
    ADD CONSTRAINT source_identity_organization_transaction_fkey
    FOREIGN KEY (organization_id, transaction_id)
    REFERENCES core.transactions (organization_id, transaction_id)
    MATCH SIMPLE
    ON DELETE RESTRICT;


-- ============================================================
-- 6. Replace transaction audit foreign key with composite FK
-- ============================================================

ALTER TABLE ops.transaction_audit
    ADD CONSTRAINT transaction_audit_organization_transaction_fkey
    FOREIGN KEY (organization_id, transaction_id)
    REFERENCES core.transactions (organization_id, transaction_id)
    MATCH SIMPLE
    ON DELETE RESTRICT;


-- ============================================================
-- 7. Replace source identity global uniqueness indexes
-- ============================================================

DROP INDEX ops.uq_source_identity_with_account;

DROP INDEX ops.uq_source_identity_without_account;

-- New organization-owned identities.
CREATE UNIQUE INDEX uq_source_identity_org_with_account
    ON ops.source_transaction_identity (
        organization_id,
        source_id,
        source_account_id,
        source_transaction_id
    )
    WHERE organization_id IS NOT NULL
      AND source_account_id IS NOT NULL;

CREATE UNIQUE INDEX uq_source_identity_org_without_account
    ON ops.source_transaction_identity (
        organization_id,
        source_id,
        source_transaction_id
    )
    WHERE organization_id IS NOT NULL
      AND source_account_id IS NULL;

-- Preserve uniqueness for historical unassigned identities.
CREATE UNIQUE INDEX uq_source_identity_legacy_with_account
    ON ops.source_transaction_identity (
        source_id,
        source_account_id,
        source_transaction_id
    )
    WHERE organization_id IS NULL
      AND source_account_id IS NOT NULL;

CREATE UNIQUE INDEX uq_source_identity_legacy_without_account
    ON ops.source_transaction_identity (
        source_id,
        source_transaction_id
    )
    WHERE organization_id IS NULL
      AND source_account_id IS NULL;


-- ============================================================
-- 8. Add organization indexes
-- ============================================================

CREATE INDEX idx_raw_transactions_organization
    ON raw.transactions (organization_id);

CREATE INDEX idx_staging_transactions_organization
    ON staging.transactions (organization_id);

CREATE INDEX idx_core_transactions_organization
    ON core.transactions (organization_id);

CREATE INDEX idx_source_identity_organization
    ON ops.source_transaction_identity (organization_id);

CREATE INDEX idx_transaction_audit_organization
    ON ops.transaction_audit (organization_id);

COMMIT;
