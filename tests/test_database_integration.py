import pytest

from src.database.connection import get_database_connection
from src.validation.validate_transactions import validate_transactions
from src.deduplication.deduplicate_transactions import (
    deduplicate_transactions
)
from src.monitoring.pipeline_status import mark_pipeline_run_failed

#a reusable raw transaction insertion helper
def insert_raw_transaction(
    run_id,
    transaction_id,
    amount="1500.00",
):
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
                    amount,
                    "KES",
                    "MPESA",
                    "COMPLETED",
                    "integration_test.csv",
                    run_id,
                ),
            )

            return cursor.fetchone()[0]

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
#cleans up after the test

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

#Test3
#Invalid transaction rejection
#Test that an invalid raw transaction is:
# Not inserted into staging
# Recorded in ops.pipeline_errors
# Counted as one rejected record in ops.pipeline_runs
# Associated with the correct pipeline run and raw record

def test_invalid_transaction_is_rejected_and_recorded(database_test_context):

    run_id = database_test_context["run_id"]
    transaction_id = (
        f"{database_test_context['prefix']}_INVALID"
    )

    # Insert an invalid raw transaction.
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
                    "CUST_TEST002",
                    "2026-11-12T14:30:00+03:00",
                    "PAYMENT",
                    "-500.00",
                    "KES",
                    "MPESA",
                    "COMPLETED",
                    "integration_test.csv",
                    run_id,
                ),
            )

            raw_id = cursor.fetchone()[0]

    # Execute actual validation.
    validate_transactions(run_id)

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Verify it was not staged.
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM staging.transactions
                WHERE raw_id = %s
                """,
                (raw_id,),
            )

            staged_count = cursor.fetchone()[0]

            # Verify the rejection was recorded.
            cursor.execute(
                """
                SELECT error_reason
                FROM ops.pipeline_errors
                WHERE raw_id = %s
                """,
                (raw_id,),
            )

            errors = [
                row[0] for row in cursor.fetchall()
            ]

            # Verify the rejected record count.
            cursor.execute(
                """
                SELECT records_rejected
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            rejected_count = cursor.fetchone()[0]

    assert staged_count == 0
    assert "amount must be greater than zero" in errors
    assert rejected_count == 1

#Test4
#Deduplication and core promotion
# Unique transaction: promoted into core.transactions
# Exact duplicate: one copy retained, the redundant copy classified correctly
# Conflicting duplicate: both versions quarantined, neither promoted
    
# --Test unique transaction promotion
# verifies that a valid, unique transaction reaches the core table
def test_unique_transaction_is_promoted_to_core(database_test_context):

    run_id = database_test_context["run_id"]
    transaction_id = (
        f"{database_test_context['prefix']}_UNIQUE"
    )

    database_test_context["transaction_ids"].append(
        transaction_id
    )

    insert_raw_transaction(run_id, transaction_id)

    # Validate and stage the transaction.
    validate_transactions(run_id)

    # Deduplicate and promote to core.
    deduplicate_transactions(run_id)

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.transactions
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )

            core_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT deduplication_status
                FROM staging.transactions
                WHERE transaction_id = %s
                    AND run_id = %s
                """,
                (transaction_id, run_id),
            )

            classification = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            promotion_metrics = cursor.fetchone()

    assert core_count == 1
    assert classification == "UNIQUE"
    assert promotion_metrics == (1, 1, 0)

# --Test exact duplicate handling
# verifies that two identical records produce one core transaction and one tracked redundant record
def test_exact_duplicates_promote_only_one_record(database_test_context):

    run_id = database_test_context["run_id"]
    transaction_id = (
        f"{database_test_context['prefix']}_EXACT"
    )

    database_test_context["transaction_ids"].append(
        transaction_id
    )

    # Insert two identical transactions.
    insert_raw_transaction(run_id, transaction_id)
    insert_raw_transaction(run_id, transaction_id)

    validate_transactions(run_id)
    deduplicate_transactions(run_id)

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT deduplication_status, COUNT(*)
                FROM staging.transactions
                WHERE transaction_id = %s
                    AND run_id = %s
                GROUP BY deduplication_status
                """,
                (transaction_id, run_id),
            )

            classifications = dict(cursor.fetchall())

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.transactions
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )

            core_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            promotion_metrics = cursor.fetchone()

    assert classifications["UNIQUE"] == 1
    assert classifications["EXACT_DUPLICATE"] == 1
    assert core_count == 1
    assert promotion_metrics == (1, 1, 0)

# --Test conflicting duplicate handling
# verifies that two conflicting records are quarantined and not promoted to core
def test_conflicting_duplicates_are_quarantined(database_test_context):

    run_id = database_test_context["run_id"]
    transaction_id = (
        f"{database_test_context['prefix']}_CONFLICT"
    )

    database_test_context["transaction_ids"].append(
        transaction_id
    )

    # Same transaction ID, different amounts.
    insert_raw_transaction(
        run_id,
        transaction_id,
        amount="1500.00",
    )

    insert_raw_transaction(
        run_id,
        transaction_id,
        amount="2500.00",
    )

    validate_transactions(run_id)
    deduplicate_transactions(run_id)

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM staging.transactions
                WHERE transaction_id = %s
                    AND run_id = %s
                    AND deduplication_status = 'CONFLICTING_DUPLICATE'
                """,
                (transaction_id, run_id),
            )

            conflicting_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.transactions
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )

            core_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            promotion_metrics = cursor.fetchone()

    assert conflicting_count == 2
    assert core_count == 0
    assert promotion_metrics == (0, 0, 0)

#Test5
#Pipeline failure handling
#verify that when a processing stage fails, the run is marked FAILED
#  and receives a completion timestamp

# --Test deduplication failure handling
def test_deduplication_failure_marks_pipeline_run_failed(
    database_test_context,
):

    run_id = database_test_context["run_id"]

    # No staged transactions exist for this run.
    # Deduplication should therefore fail.
    with pytest.raises(
        ValueError,
        match="No staged transactions found",
    ):
        deduplicate_transactions(run_id)

    # Verify that the failure was recorded.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT run_status, completed_at
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            result = cursor.fetchone()

    assert result is not None
    assert result[0] == "FAILED"
    assert result[1] is not None

# --Test completed runs cannot be overwritten
# verifies that our failure handler only changes runs that are still RUNNING
def test_failure_handler_does_not_overwrite_successful_run(
    database_test_context,
):

    run_id = database_test_context["run_id"]

    # Mark the run as successfully completed.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET run_status = 'SUCCESS',
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (run_id,),
            )

    # Attempt to mark the successful run as failed.
    result = mark_pipeline_run_failed(run_id)

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT run_status
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            final_status = cursor.fetchone()[0]

    assert result is False
    assert final_status == "SUCCESS"

#Test6
#Test transaction in core table is not promoted again
def test_existing_core_transaction_is_not_promoted_again(
    database_test_context,
):

    run_id = database_test_context["run_id"]
    transaction_id = (
        f"{database_test_context['prefix']}_EXISTING"
    )

    database_test_context["transaction_ids"].append(
        transaction_id
    )

    # Insert the transaction into core first.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO core.transactions (
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    payment_method,
                    status
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
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
                ),
            )

    # Submit the same transaction through the pipeline.
    insert_raw_transaction(run_id, transaction_id)

    validate_transactions(run_id)
    deduplicate_transactions(run_id)

    # Verify promotion metrics and core record count.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            promotion_metrics = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM core.transactions
                WHERE transaction_id = %s
                """,
                (transaction_id,),
            )

            core_count = cursor.fetchone()[0]

    assert promotion_metrics == (1, 0, 1)
    assert core_count == 1