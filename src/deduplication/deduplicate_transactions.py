import argparse
from collections import defaultdict

from src.database.connection import get_database_connection
from src.monitoring.pipeline_status import mark_pipeline_run_failed

def get_transaction_signature(record):
    return (
        record["customer_id"],
        record["transaction_date"],
        record["transaction_type"],
        record["amount"],
        record["currency"],
        record["payment_method"],
        record["status"],
    )


def _deduplicate_transactions(run_id):
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT run_id
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            if cursor.fetchone() is None:
                raise ValueError(
                    f"Pipeline run {run_id} does not exist."
                )

            cursor.execute(
                """
                SELECT
                    staging_id,
                    raw_id,
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    payment_method,
                    status
                FROM staging.transactions
                WHERE run_id = %s
                ORDER BY raw_id
                """,
                (run_id,),
            )

            rows = cursor.fetchall()

            if not rows:
                raise ValueError(
                    f"No staged transactions found for run {run_id}."
                )

            # Group records by transaction ID.
            groups = defaultdict(list)

            for row in rows:
                (
                    staging_id,
                    raw_id,
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    payment_method,
                    status,
                ) = row

                record = {
                    "staging_id": staging_id,
                    "raw_id": raw_id,
                    "transaction_id": transaction_id,
                    "customer_id": customer_id,
                    "transaction_date": transaction_date,
                    "transaction_type": transaction_type,
                    "amount": amount,
                    "currency": currency,
                    "payment_method": payment_method,
                    "status": status,
                }

                groups[transaction_id].append(record)

            classifications = []
            unique_records = []

            exact_duplicate_count = 0
            conflicting_record_count = 0
            exact_duplicate_id_count = 0
            conflicting_id_count = 0

            # Classify each transaction ID group.
            for transaction_id, records in groups.items():

                if len(records) == 1:
                    record = records[0]

                    classifications.append(
                        (
                            "UNIQUE",
                            None,
                            record["staging_id"],
                        )
                    )

                    unique_records.append(record)
                    continue

                signatures = {
                    get_transaction_signature(record)
                    for record in records
                }

                if len(signatures) == 1:
                    # Identical transaction records.
                    records.sort(
                        key=lambda record: record["raw_id"]
                    )

                    keeper = records[0]

                    classifications.append(
                        (
                            "UNIQUE",
                            None,
                            keeper["staging_id"],
                        )
                    )

                    unique_records.append(keeper)

                    for duplicate in records[1:]:
                        classifications.append(
                            (
                                "EXACT_DUPLICATE",
                                keeper["raw_id"],
                                duplicate["staging_id"],
                            )
                        )

                        exact_duplicate_count += 1

                    exact_duplicate_id_count += 1

                else:
                    # Conflicting versions: quarantine all versions.
                    for record in records:
                        classifications.append(
                            (
                                "CONFLICTING_DUPLICATE",
                                None,
                                record["staging_id"],
                            )
                        )

                    conflicting_record_count += len(records)
                    conflicting_id_count += 1

            # Check existing core records before inserting.
            transaction_ids = [
                record["transaction_id"]
                for record in unique_records
            ]

            cursor.execute(
                """
                SELECT
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    payment_method,
                    status
                FROM core.transactions
                WHERE transaction_id = ANY(%s)
                """,
                (transaction_ids,),
            )

            existing_core = {
                row[0]: row[1:]
                for row in cursor.fetchall()
            }

            core_records = []

            for record in unique_records:
                transaction_id = record["transaction_id"]

                signature = get_transaction_signature(record)

                if transaction_id in existing_core:
                    if existing_core[transaction_id] != signature:
                        raise ValueError(
                            "Core transaction conflict detected for "
                            f"{transaction_id}. Processing stopped."
                        )

                    # An identical transaction is already in core.
                    continue

                core_records.append(
                    (
                        record["transaction_id"],
                        record["customer_id"],
                        record["transaction_date"],
                        record["transaction_type"],
                        record["amount"],
                        record["currency"],
                        record["payment_method"],
                        record["status"],
                    )
                )

            # Save classifications.
            cursor.executemany(
                """
                UPDATE staging.transactions
                SET deduplication_status = %s,
                    duplicate_of_raw_id = %s
                WHERE staging_id = %s
                """,
                classifications,
            )

            # Promote eligible transactions to core.
            if core_records:
                cursor.executemany(
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
                    core_records,
                )

            # Update pipeline duplicate count.
            records_duplicated = (
                exact_duplicate_count + conflicting_record_count
            )

            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET records_duplicated = %s
                WHERE run_id = %s
                """,
                (records_duplicated, run_id),
            )

            # Update pipeline status to SUCCESS
            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET run_status = 'SUCCESS'
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                    AND run_status = 'RUNNING'
                """,
                (run_id,),
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    f"Pipeline run {run_id} is not in RUNNING state."
                )

    print("DEDUPLICATION COMPLETED")
    print("-----------------------")
    print(f"Pipeline run ID: {run_id}")
    print(f"Staged records examined: {len(rows)}")
    print(
        "Unique transaction IDs: "
        f"{len(groups) - exact_duplicate_id_count - conflicting_id_count}"
    )
    print(f"Exact duplicate IDs: {exact_duplicate_id_count}")
    print(f"Redundant exact records: {exact_duplicate_count}")
    print(f"Conflicting transaction IDs: {conflicting_id_count}")
    print(f"Conflicting records quarantined: {conflicting_record_count}")
    print(f"Records promoted to core: {len(core_records)}")
    print(f"Records promoted to core: {len(core_records)}")

#integrate the failure handler
#add a wrapper(lets us catch failures w/o indenting or rewriting the deduplication function)
#failure handler uses a separate connection, so it can record the failure after the original transaction rolls back
def deduplicate_transactions(run_id):
    try:
        _deduplicate_transactions(run_id)
    except Exception as e:
        print(f"Error during deduplication: {e}")
        mark_pipeline_run_failed(run_id)
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deduplicate and load trusted transactions."
    )

    parser.add_argument(
        "--run-id",
        type=int,
        required=True,
        help="Pipeline run ID to process.",
    )

    arguments = parser.parse_args()

    deduplicate_transactions(arguments.run_id)