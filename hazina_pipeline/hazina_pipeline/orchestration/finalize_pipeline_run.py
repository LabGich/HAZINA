# Locks the parent run
# Checks that all child executions are terminal
# Aggregates counters from all child executions
# Determines the parent status using our agreed rules
# Sets the parent's completion timestamp
# Does not overwrite child execution results
# A parent must not be finalized while any child is still PENDING or RUNNING


from hazina_pipeline.database.connection import get_database_connection


class PipelineRunFinalizationError(RuntimeError):
    """Raised when a pipeline run cannot be finalized."""


def finalize_pipeline_run(run_id):
    """Aggregate child execution results and finalize a V2 pipeline run."""

    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise ValueError("run_id must be a positive integer")

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Lock the parent run.
            cursor.execute(
                """
                SELECT run_status
                FROM ops.pipeline_runs
                WHERE run_id = %s
                FOR UPDATE
                """,
                (run_id,),
            )

            parent = cursor.fetchone()

            if parent is None:
                raise PipelineRunFinalizationError(
                    f"Pipeline run {run_id} does not exist."
                )

            parent_status = parent[0]

            if parent_status not in ("RUNNING", "CANCELLED"):
                raise PipelineRunFinalizationError(
                    f"Cannot finalize pipeline run with status "
                    f"{parent_status}."
                )

            # Lock all child executions and retrieve their counters.
            cursor.execute(
                """
                SELECT
                    execution_status,
                    records_received,
                    records_loaded,
                    records_rejected,
                    records_skipped,
                    records_updated,
                    records_duplicated,
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core
                FROM ops.source_executions
                WHERE run_id = %s
                ORDER BY source_execution_id
                FOR UPDATE
                """,
                (run_id,),
            )

            executions = cursor.fetchall()

            if not executions:
                raise PipelineRunFinalizationError(
                    "Cannot finalize a pipeline run without "
                    "source executions."
                )

            terminal_statuses = {
                "SUCCESS",
                "PARTIAL_SUCCESS",
                "FAILED",
                "SKIPPED",
                "CANCELLED",
            }

            for execution in executions:
                if execution[0] not in terminal_statuses:
                    raise PipelineRunFinalizationError(
                        "Cannot finalize pipeline run: at least one "
                        "source execution is still pending or running."
                    )

            # Aggregate all child execution counters.
            counter_columns = [
                "records_received",
                "records_loaded",
                "records_rejected",
                "records_skipped",
                "records_updated",
                "records_duplicated",
                "records_unique_eligible",
                "records_promoted",
                "records_already_in_core",
            ]

            totals = {
                column: sum(execution[index + 1] for execution in executions)
                for index, column in enumerate(counter_columns)
            }

            child_statuses = [execution[0] for execution in executions]

            # An explicitly cancelled parent remains CANCELLED.
            if parent_status == "CANCELLED":
                final_status = "CANCELLED"
            elif all(status == "SUCCESS" for status in child_statuses):
                final_status = "SUCCESS"
            elif any(
                status in ("SUCCESS", "PARTIAL_SUCCESS")
                for status in child_statuses
            ):
                final_status = "PARTIAL_SUCCESS"
            else:
                final_status = "FAILED"

            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET
                    run_status = %s,
                    records_received = %s,
                    records_loaded = %s,
                    records_rejected = %s,
                    records_skipped = %s,
                    records_updated = %s,
                    records_duplicated = %s,
                    records_unique_eligible = %s,
                    records_promoted = %s,
                    records_already_in_core = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                RETURNING
                    run_id,
                    run_status,
                    records_received,
                    records_loaded,
                    records_rejected,
                    records_skipped,
                    records_updated,
                    records_duplicated,
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core,
                    completed_at
                """,
                (
                    final_status,
                    totals["records_received"],
                    totals["records_loaded"],
                    totals["records_rejected"],
                    totals["records_skipped"],
                    totals["records_updated"],
                    totals["records_duplicated"],
                    totals["records_unique_eligible"],
                    totals["records_promoted"],
                    totals["records_already_in_core"],
                    run_id,
                ),
            )

            result = cursor.fetchone()

    return {
        "run_id": result[0],
        "run_status": result[1],
        "records_received": result[2],
        "records_loaded": result[3],
        "records_rejected": result[4],
        "records_skipped": result[5],
        "records_updated": result[6],
        "records_duplicated": result[7],
        "records_unique_eligible": result[8],
        "records_promoted": result[9],
        "records_already_in_core": result[10],
        "completed_at": result[11],
    }

