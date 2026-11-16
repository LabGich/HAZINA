UPDATE ops.pipeline_runs
SET
    records_unique_eligible = CASE
        WHEN run_id IN (1, 3, 4) THEN 840
        ELSE 0
    END,

    records_promoted = CASE
        WHEN run_id = 1 THEN 840
        ELSE 0
    END,

    records_already_in_core = CASE
        WHEN run_id IN (3, 4) THEN 840
        ELSE 0
    END

WHERE run_id IN (1, 2, 3, 4);