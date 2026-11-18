
from hazina_pipeline.database.connection import get_database_connection


class SourceExecutionFinalizationError(RuntimeError):
    """Raised when a source execution cannot be finalized."""


def finalize_source_execution(run_id, source_execution_id):
    """
    Finalize a completed V2 source execution.

    The parent pipeline run is deliberately not modified.
    """

    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ValueError("run_id must be a positive integer")

    if (
        not isinstance(source_execution_id, int)
        or isinstance(source_execution_id, bool)
        or source_execution_id <= 0
    ):
        raise ValueError("source_execution_id must be a positive integer")

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Lock the execution and retrieve its parent run's ownership.
            cursor.execute(
                """
                SELECT
                    se.execution_status,
                    se.records_rejected,
                    se.records_skipped,
                    pr.organization_id
                FROM ops.source_executions se
                JOIN ops.pipeline_runs pr
                    ON pr.run_id = se.run_id
                WHERE se.run_id = %s
                  AND se.source_execution_id = %s
                FOR UPDATE OF se
                """,
                (run_id, source_execution_id),
            )

            execution = cursor.fetchone()

            if execution is None:
                raise SourceExecutionFinalizationError(
                    "Source execution does not exist or does not belong "
                    "to the specified pipeline run."
                )

            (
                execution_status,
                records_rejected,
                records_skipped,
                organization_id,
            ) = execution

            if execution_status != "RUNNING":
                raise SourceExecutionFinalizationError(
                    f"Cannot finalize execution with status "
                    f"{execution_status}. Expected RUNNING."
                )

            # Ensure pending records belong to the same organization
            # as the parent pipeline run. NULL supports legacy runs.
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM staging.transactions
                WHERE run_id = %s
                  AND source_execution_id = %s
                  AND organization_id IS NOT DISTINCT FROM %s
                  AND (
                      validation_status = 'PENDING'
                      OR (
                          validation_status = 'VALID'
                          AND deduplication_status = 'PENDING'
                      )
                  )
                """,
                (run_id, source_execution_id, organization_id),
            )

            pending_records = cursor.fetchone()[0]

            if pending_records:
                raise SourceExecutionFinalizationError(
                    f"Cannot finalize execution: {pending_records} "
                    "staged records are still awaiting validation "
                    "or deduplication."
                )

            # Completed processing with rejected or skipped records
            # is a partial success, not a fatal execution failure.
            if records_rejected > 0 or records_skipped > 0:
                final_status = "PARTIAL_SUCCESS"
            else:
                final_status = "SUCCESS"

            cursor.execute(
                """
                UPDATE ops.source_executions
                SET
                    execution_status = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE source_execution_id = %s
                  AND run_id = %s
                  AND execution_status = 'RUNNING'
                RETURNING
                    source_execution_id,
                    execution_status,
                    records_received,
                    records_loaded,
                    records_mapped,
                    records_rejected,
                    records_skipped,
                    records_duplicated,
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core,
                    completed_at
                """,
                (final_status, source_execution_id, run_id),
            )

            result = cursor.fetchone()

            if result is None:
                raise SourceExecutionFinalizationError(
                    "Source execution could not be finalized."
                )

    return {
        "source_execution_id": result[0],
        "execution_status": result[1],
        "records_received": result[2],
        "records_loaded": result[3],
        "records_mapped": result[4],
        "records_rejected": result[5],
        "records_skipped": result[6],
        "records_duplicated": result[7],
        "records_unique_eligible": result[8],
        "records_promoted": result[9],
        "records_already_in_core": result[10],
        "completed_at": result[11],
    }
