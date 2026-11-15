# Accept run_id, source_execution_id, error_code, and error_message
# Lock the source execution
# Verify it belongs to the specified run and is currently RUNNING
# Set execution_status = 'FAILED'
# Store error_code, error_message, and completed_at
# Preserve all counters already recorded
# Never modify the parent run


from src.database.connection import get_database_connection


class SourceExecutionFailureError(RuntimeError):
    """Raised when a source execution cannot be marked as failed."""


def fail_source_execution(
    run_id,
    source_execution_id,
    error_code,
    error_message,
):
    """
    Mark a running V2 source execution as FAILED.

    Preserves existing processing counters and does not modify
    the parent pipeline run.
    """

    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ValueError("run_id must be a positive integer")

    if (
        not isinstance(source_execution_id, int)
        or isinstance(source_execution_id, bool)
        or source_execution_id <= 0
    ):
        raise ValueError("source_execution_id must be a positive integer")

    if not isinstance(error_code, str) or not error_code.strip():
        raise ValueError("error_code must be a non-empty string")

    if not isinstance(error_message, str) or not error_message.strip():
        raise ValueError("error_message must be a non-empty string")

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Lock the execution and verify ownership and status.
            cursor.execute(
                """
                SELECT execution_status
                FROM ops.source_executions
                WHERE run_id = %s
                  AND source_execution_id = %s
                FOR UPDATE
                """,
                (run_id, source_execution_id),
            )

            execution = cursor.fetchone()

            if execution is None:
                raise SourceExecutionFailureError(
                    "Source execution does not exist or does not belong "
                    "to the specified pipeline run."
                )

            if execution[0] != "RUNNING":
                raise SourceExecutionFailureError(
                    f"Cannot fail execution with status {execution[0]}. "
                    "Expected RUNNING."
                )

            cursor.execute(
                """
                UPDATE ops.source_executions
                SET
                    execution_status = 'FAILED',
                    error_code = %s,
                    error_message = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                  AND source_execution_id = %s
                  AND execution_status = 'RUNNING'
                RETURNING
                    source_execution_id,
                    execution_status,
                    error_code,
                    error_message,
                    completed_at
                """,
                (
                    error_code.strip(),
                    error_message.strip(),
                    run_id,
                    source_execution_id,
                ),
            )

            result = cursor.fetchone()

            if result is None:
                raise SourceExecutionFailureError(
                    "Source execution could not be marked as failed."
                )

    return {
        "source_execution_id": result[0],
        "execution_status": result[1],
        "error_code": result[2],
        "error_message": result[3],
        "completed_at": result[4],
    }
