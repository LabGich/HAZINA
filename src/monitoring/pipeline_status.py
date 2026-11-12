# Failure handling for pipeline status monitoring
# when a Psycopg connection transaction fails, its changes are rolled back
# therefore, we must record FAILED using a separate database connection
# -- after the failed transaction has rolled back

from src.database.connection import get_database_connection


def mark_pipeline_run_failed(run_id):
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET run_status = 'FAILED',
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                    AND run_status = 'RUNNING'
                """,
                (run_id,),
            )

            return cursor.rowcount == 1

# monitoring retrieval func
#return as a py dict
def get_pipeline_run_summary(run_id):

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    run_id,
                    source_file,
                    started_at,
                    completed_at,
                    run_status,
                    records_received,
                    records_loaded,
                    records_rejected,
                    records_duplicated
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            result = cursor.fetchone()

            if result is None:
                raise ValueError(
                    f"Pipeline run {run_id} does not exist."
                )

            columns = [
                description.name
                for description in cursor.description
            ]

            return dict(zip(columns, result))
