# Start a pending source execution.
# Verify the parent pipeline run is RUNNING.
# Verify the source execution belongs to the supplied run.
# Lock both records to prevent concurrent lifecycle changes.
# Set execution_status to RUNNING and record started_at.
# Do not modify the parent pipeline run or any counters.


from src.database.connection import get_database_connection


class SourceExecutionStartError(RuntimeError):
    """Raised when a source execution cannot be started."""


def start_source_execution(run_id, source_execution_id):
    """
    Start one PENDING source execution belonging to a RUNNING pipeline run.

    Returns the execution ID, run ID, status, and start timestamp.
    """

    if (
        not isinstance(run_id, int)
        or isinstance(run_id, bool)
        or run_id <= 0
    ):
        raise ValueError("run_id must be a positive integer.")

    if (
        not isinstance(source_execution_id, int)
        or isinstance(source_execution_id, bool)
        or source_execution_id <= 0
    ):
        raise ValueError(
            "source_execution_id must be a positive integer."
        )

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Lock the parent first to maintain a consistent lock order.
            cursor.execute(
                """
                SELECT run_id, run_status
                FROM ops.pipeline_runs
                WHERE run_id = %s
                FOR UPDATE
                """,
                (run_id,),
            )

            run = cursor.fetchone()

            if run is None:
                raise SourceExecutionStartError(
                    f"Pipeline run {run_id} does not exist."
                )

            if run[1] != "RUNNING":
                raise SourceExecutionStartError(
                    f"Pipeline run {run_id} is not RUNNING. "
                    f"Current status: {run[1]}."
                )

            # Lock and verify the requested source execution.
            cursor.execute(
                """
                SELECT
                    source_execution_id,
                    run_id,
                    execution_status,
                    started_at
                FROM ops.source_executions
                WHERE source_execution_id = %s
                  AND run_id = %s
                FOR UPDATE
                """,
                (source_execution_id, run_id),
            )

            execution = cursor.fetchone()

            if execution is None:
                raise SourceExecutionStartError(
                    f"Source execution {source_execution_id} "
                    f"does not belong to pipeline run {run_id}."
                )

            if execution[2] != "PENDING":
                raise SourceExecutionStartError(
                    f"Source execution {source_execution_id} "
                    f"cannot be started. "
                    f"Current status: {execution[2]}."
                )

            # Transition the execution from PENDING to RUNNING.
            cursor.execute(
                """
                UPDATE ops.source_executions
                SET
                    execution_status = 'RUNNING',
                    started_at = CURRENT_TIMESTAMP
                WHERE source_execution_id = %s
                  AND run_id = %s
                  AND execution_status = 'PENDING'
                RETURNING
                    source_execution_id,
                    run_id,
                    execution_status,
                    started_at
                """,
                (source_execution_id, run_id),
            )

            started_execution = cursor.fetchone()

            if started_execution is None:
                raise SourceExecutionStartError(
                    f"Failed to start source execution "
                    f"{source_execution_id}."
                )

    return {
        "source_execution_id": started_execution[0],
        "run_id": started_execution[1],
        "execution_status": started_execution[2],
        "started_at": started_execution[3],
    }