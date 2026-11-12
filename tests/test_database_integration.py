
from src.database.connection import get_database_connection


def test_database_connection_and_pipeline_run(database_test_context):

    run_id = database_test_context["run_id"]

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT run_status, source_file
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            result = cursor.fetchone()

    assert result is not None
    assert result[0] == "RUNNING"
    assert result[1] == (
        f"{database_test_context['prefix']}.csv"
    )
