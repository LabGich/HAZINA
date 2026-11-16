-- central operational reporting view
-- - as we process additional pipeline runs, the same view will automatically include their metrics
-- resolved an important SQL issue: join fan-out
-- by aggregating each table independently before joining, we avoid inflated monitoring metrics
CREATE OR REPLACE VIEW ops.pipeline_monitoring AS

WITH error_summary AS (
    SELECT
        run_id,
        COUNT(DISTINCT raw_id) AS rejected_records
    FROM ops.pipeline_errors
    GROUP BY run_id
),

staging_summary AS (
    SELECT
        run_id,
        COUNT(*) AS records_staged,

        COUNT(*) FILTER (
            WHERE deduplication_status = 'UNIQUE'
        ) AS unique_records,

        COUNT(*) FILTER (
            WHERE deduplication_status = 'EXACT_DUPLICATE'
        ) AS exact_duplicates,

        COUNT(*) FILTER (
            WHERE deduplication_status = 'CONFLICTING_DUPLICATE'
        ) AS conflicting_duplicates

    FROM staging.transactions
    GROUP BY run_id
)

SELECT
    pr.run_id,
    pr.source_file,
    pr.started_at,
    pr.completed_at,
    pr.run_status,
    pr.records_received,
    pr.records_loaded AS records_staged,
    pr.records_rejected,
    pr.records_duplicated,

    COALESCE(es.rejected_records, 0) AS rejected_records,
    COALESCE(ss.unique_records, 0) AS unique_records,
    COALESCE(ss.exact_duplicates, 0) AS exact_duplicates,
    COALESCE(ss.conflicting_duplicates, 0)
        AS conflicting_duplicates

FROM ops.pipeline_runs pr

LEFT JOIN error_summary es
    ON pr.run_id = es.run_id

LEFT JOIN staging_summary ss
    ON pr.run_id = ss.run_id;