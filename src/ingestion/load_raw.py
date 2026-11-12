
from pathlib import Path

import pandas as pd

from src.database.connection import get_database_connection
from src.monitoring.pipeline_status import mark_pipeline_run_failed


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_FILE = PROJECT_ROOT / "data" / "sample" / "hazina_transactions.csv"

EXPECTED_COLUMNS = [
    "transaction_id",
    "customer_id",
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
    "payment_method",
    "status",
]


def load_raw_transactions():

    # Create and commit the pipeline run independently.
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
                (CSV_FILE.name,),
            )

            run_id = cursor.fetchone()[0]

    try:
        if not CSV_FILE.exists():
            raise FileNotFoundError(
                f"CSV file not found: {CSV_FILE}"
            )

        dataframe = pd.read_csv(
            CSV_FILE,
            dtype=str,
            keep_default_na=False,
        )

        if list(dataframe.columns) != EXPECTED_COLUMNS:
            raise ValueError(
                "CSV columns do not match the approved specification."
            )

        insert_sql = """
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
        """

        records = [
            tuple(row) + (CSV_FILE.name, run_id)
            for row in dataframe.itertuples(
                index=False,
                name=None,
            )
        ]

        # Load raw records in a separate transaction.
        with get_database_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE ops.pipeline_runs
                    SET records_received = %s
                    WHERE run_id = %s
                    """,
                    (len(dataframe), run_id),
                )

                cursor.executemany(insert_sql, records)

    except Exception:
        mark_pipeline_run_failed(run_id)
        raise

    print("RAW INGESTION COMPLETED")
    print("-----------------------")
    print(f"Pipeline run ID: {run_id}")
    print(f"Source file: {CSV_FILE.name}")
    print(f"Records received: {len(dataframe)}")
    print(f"Records loaded into raw: {len(records)}")
    print("Pipeline status: RUNNING")

    #for next stages and the pipeline orchestrator to know which execution to process
    return run_id


if __name__ == "__main__":
    load_raw_transactions()