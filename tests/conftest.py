# shared db test fixture
# Creates a unique test pipeline run
# Supplies its run_id to individual tests
# Tracks transaction IDs inserted into core
# Deletes test data after each test
# Cleans up even when a test fails

import uuid

import pytest

from src.database.connection import get_database_connection


@pytest.fixture
def database_test_context():

    # Generate a unique prefix for this test.
    prefix = f"TEST_{uuid.uuid4().hex[:12].upper()}"

    transaction_ids = []

    # Create a dedicated pipeline run.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO ops.pipeline_runs (
                    source_file,
                    run_status
                )
                VALUES (%s, 'RUNNING')
                RETURNING run_id
                """,
                (f"{prefix}.csv",),
            )

            run_id = cursor.fetchone()[0]

    context = {
        "run_id": run_id,
        "prefix": prefix,
        "transaction_ids": transaction_ids,
    }

    yield context

    # Automatically clean up test records.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            if transaction_ids:
                cursor.execute(
                    """
                    DELETE FROM core.transactions
                    WHERE transaction_id = ANY(%s)
                    """,
                    (transaction_ids,),
                )

            cursor.execute(
                """
                DELETE FROM ops.pipeline_errors
                WHERE run_id = %s
                """,
                (run_id,),
            )

            cursor.execute(
                """
                DELETE FROM staging.transactions
                WHERE run_id = %s
                """,
                (run_id,),
            )

            cursor.execute(
                """
                DELETE FROM raw.transactions
                WHERE run_id = %s
                """,
                (run_id,),
            )

            cursor.execute(
                """
                DELETE FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )