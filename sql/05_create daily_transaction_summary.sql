CREATE OR REPLACE VIEW analytics.daily_transaction_summary AS
SELECT
    (transaction_date AT TIME ZONE 'UTC')::DATE AS transaction_date,
    currency,
    status,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS average_amount
FROM core.transactions
GROUP BY
    (transaction_date AT TIME ZONE 'UTC')::DATE,
    currency,
    status;