
from src.database.connection import get_database_connection
from src.validation.validate_transactions import validate_transactions

#Test1
# This test:
# Connected to PostgreSQL
# Created a temporary pipeline run
# Retrieved and verified its status and source filename
# Cleaned up the temporary records afterward

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

#Test2
#validation databasee operation
#This test confirms the validation process:
# Reads a raw transaction from PostgreSQL.
# Validates and standardizes its fields
# Inserts the valid transaction into staging.transactions
# Preserves its raw_id and run_id
# Assigns the default deduplication status PENDING
def test_valid_transaction_is_saved_to_staging(database_test_context):

    run_id = database_test_context["run_id"]
    transaction_id = (
        f"{database_test_context['prefix']}_TXN001"
    )

    # Insert a valid raw transaction.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO raw.transactions (
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    payment_method,
                    status,
                    source_file,
                    run_id
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                RETURNING raw_id
                """,
                (
                    transaction_id,
                    "CUST_TEST001",
                    "2026-11-12T14:30:00+03:00",
                    "PAYMENT",
                    "1500.00",
                    "KES",
                    "MPESA",
                    "COMPLETED",
                    "integration_test.csv",
                    run_id,
                ),
            )

            raw_id = cursor.fetchone()[0]

    # Execute the actual validation database operation.
    validate_transactions(run_id)

    # Verify that the transaction was saved to staging.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    transaction_id,
                    raw_id,
                    run_id,
                    amount,
                    deduplication_status
                FROM staging.transactions
                WHERE raw_id = %s
                """,
                (raw_id,),
            )

            staged_record = cursor.fetchone()

    assert staged_record is not None
    assert staged_record[0] == transaction_id
    assert staged_record[1] == raw_id
    assert staged_record[2] == run_id
    assert staged_record[3] == 1500.00
    assert staged_record[4] == "PENDING"
