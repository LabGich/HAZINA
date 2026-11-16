ALTER TABLE staging.transactions
ADD COLUMN validation_status VARCHAR(20)
NOT NULL DEFAULT 'PENDING';

ALTER TABLE staging.transactions
ADD CONSTRAINT chk_staging_validation_status
CHECK (
    validation_status IN ('PENDING', 'VALID', 'INVALID')
);

CREATE INDEX idx_staging_validation_status
ON staging.transactions(validation_status);