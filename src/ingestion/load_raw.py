
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv


# ---------------------------------------------------------
# PROJECT CONFIGURATION
# ---------------------------------------------------------

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


# Load environment variables from the project root.
load_dotenv(PROJECT_ROOT / ".env")


def get_database_connection():
    """Create a PostgreSQL connection using .env settings."""

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing:
        raise ValueError(
            f"Missing database environment variables: {missing}"
        )

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_raw_transactions():
    """Load the source CSV into raw.transactions."""

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"CSV file not found: {CSV_FILE}"
        )

    # Read every field as text and preserve empty values.
    dataframe = pd.read_csv(
        CSV_FILE,
        dtype=str,
        keep_default_na=False,
    )

    # Confirm the expected input structure.
    if list(dataframe.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "CSV columns do not match the approved specification."
        )

    records = [
        tuple(row) + (CSV_FILE.name,)
        for row in dataframe.itertuples(
            index=False,
            name=None,
        )
    ]

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
            source_file
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Register this pipeline execution.
            cursor.execute(
                """
                INSERT INTO ops.pipeline_runs (
                    source_file,
                    run_status,
                    records_received
                )
                VALUES (%s, 'RUNNING', %s)
                RETURNING run_id
                """,
                (CSV_FILE.name, len(records)),
            )

            run_id = cursor.fetchone()[0]

            # Insert all original CSV records.
            cursor.executemany(insert_sql, records)

            # Mark the execution as successful.
            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET
                    run_status = 'SUCCESS',
                    records_loaded = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (len(records), run_id),
            )

    print("RAW INGESTION COMPLETED")
    print("-----------------------")
    print(f"Pipeline run ID: {run_id}")
    print(f"Source file: {CSV_FILE.name}")
    print(f"Records received: {len(records)}")
    print(f"Records loaded: {len(records)}")


if __name__ == "__main__":
    load_raw_transactions()
