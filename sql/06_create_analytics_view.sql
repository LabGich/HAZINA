-- transaction_overview provides a high-level picture of transaction activity per currency
-- transaction_status_summary allows us to compare:
-- - initiated, pending, completed, failed, and reversed transactions without mixing currencies
-- Transaction overview by currency.

CREATE OR REPLACE VIEW analytics.transaction_overview AS
SELECT
    currency,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS average_amount
FROM core.transactions
GROUP BY currency;


-- Transaction summary by currency and status.
CREATE OR REPLACE VIEW analytics.transaction_status_summary AS
SELECT
    currency,
    status,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS average_amount
FROM core.transactions
GROUP BY
    currency,
    status;