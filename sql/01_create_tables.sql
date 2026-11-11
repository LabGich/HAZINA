
-- =========================================================
-- HAZINA FINANCIAL TRANSACTIONS PIPELINE
-- Phase 1: Initial database tables
-- =========================================================

-- 1. RAW SCHEMA
-- Preserve incoming CSV values without type conversion.

CREATE TABLE IF NOT EXISTS raw.transactions (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id TEXT,
    customer_id TEXT,
    transaction_date TEXT,
    transaction_type TEXT,
    amount TEXT,
    currency TEXT,
    payment_method TEXT,
    status TEXT,
    source_file TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 2. STAGING SCHEMA
-- Store validated and standardized transaction records.

CREATE TABLE IF NOT EXISTS staging.transactions (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    transaction_date TIMESTAMPTZ NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(20, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 3. CORE SCHEMA
-- Store trusted transactions.

CREATE TABLE IF NOT EXISTS core.transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    transaction_date TIMESTAMPTZ NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount NUMERIC(20, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 4. OPS SCHEMA
-- Track pipeline executions.

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_file TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    run_status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
    records_received INTEGER NOT NULL DEFAULT 0,
    records_loaded INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    records_duplicated INTEGER NOT NULL DEFAULT 0
);


-- Track rejected records and their reasons.

CREATE TABLE IF NOT EXISTS ops.pipeline_errors (
    error_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT REFERENCES ops.pipeline_runs(run_id),
    raw_id BIGINT REFERENCES raw.transactions(raw_id),
    transaction_id TEXT,
    error_reason TEXT NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 5. ANALYTICS SCHEMA
-- Initial transaction summary reporting view.

CREATE OR REPLACE VIEW analytics.transaction_summary AS
SELECT
    currency,
    status,
    transaction_type,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS average_amount
FROM core.transactions
GROUP BY
    currency,
    status,
    transaction_type;
