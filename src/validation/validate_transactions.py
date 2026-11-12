
import os
import argparse
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


ALLOWED_TRANSACTION_TYPES = {
    "PAYMENT",
    "DEPOSIT",
    "WITHDRAWAL",
    "TRANSFER",
    "REFUND",
    "FEE",
}

ALLOWED_CURRENCIES = {"KES", "USD"}

ALLOWED_PAYMENT_METHODS = {
    "MPESA",
    "BANK_TRANSFER",
    "CARD",
    "CASH",
    "DIGITAL_WALLET",
    "USSD",
    "AGENT",
}

ALLOWED_STATUSES = {
    "INITIATED",
    "PENDING",
    "COMPLETED",
    "FAILED",
    "REVERSED",
}


def get_database_connection():
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


def validate_record(record):
    errors = []

    transaction_id = (record["transaction_id"] or "").strip()
    customer_id = (record["customer_id"] or "").strip()
    transaction_date = (record["transaction_date"] or "").strip()
    transaction_type = (record["transaction_type"] or "").strip().upper()
    amount_value = (record["amount"] or "").strip()
    currency = (record["currency"] or "").strip().upper()
    payment_method = (record["payment_method"] or "").strip().upper()
    status = (record["status"] or "").strip().upper()

    # Required fields
    values = {
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "transaction_date": transaction_date,
        "transaction_type": transaction_type,
        "amount": amount_value,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
    }

    for field, value in values.items():
        if not value:
            errors.append(f"{field} is required")

    # Identifier lengths
    if transaction_id and len(transaction_id) > 50:
        errors.append("transaction_id exceeds 50 characters")

    if customer_id and len(customer_id) > 50:
        errors.append("customer_id exceeds 50 characters")

    # Transaction date
    parsed_date = None

    if transaction_date:
        try:
            parsed_date = datetime.fromisoformat(
                transaction_date.replace("Z", "+00:00")
            )

            if parsed_date.utcoffset() is None:
                errors.append(
                    "transaction_date must include a timezone"
                )

        except ValueError:
            errors.append("transaction_date is not a valid ISO 8601 timestamp")

    # Transaction amount
    parsed_amount = None

    if amount_value:
        try:
            parsed_amount = Decimal(amount_value)

            if not parsed_amount.is_finite():
                errors.append("amount must be a finite number")

            elif parsed_amount <= 0:
                errors.append("amount must be greater than zero")

            elif parsed_amount >= Decimal("1000000000000000000"):
                errors.append("amount exceeds NUMERIC(20,2) capacity")

            elif parsed_amount != parsed_amount.quantize(Decimal("0.01")):
                errors.append("amount cannot have more than two decimal places")

        except (InvalidOperation, ValueError):
            errors.append("amount is not a valid decimal number")

    # Transaction type
    if transaction_type and transaction_type not in ALLOWED_TRANSACTION_TYPES:
        errors.append(f"Invalid transaction_type: {transaction_type}")

    # Currency
    if currency and currency not in ALLOWED_CURRENCIES:
        errors.append(f"Invalid currency: {currency}")

    # Payment method
    if payment_method and payment_method not in ALLOWED_PAYMENT_METHODS:
        errors.append(f"Invalid payment_method: {payment_method}")

    # Transaction status
    if status and status not in ALLOWED_STATUSES:
        errors.append(f"Invalid status: {status}")

    if errors:
        return None, errors

    standardized_record = {
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "transaction_date": parsed_date,
        "transaction_type": transaction_type,
        "amount": parsed_amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": status,
    }

    return standardized_record, []


def validate_transactions(run_id):
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

            # Retrieve records not previously processed.
            cursor.execute(
                """
                SELECT
                    r.raw_id,
                    r.run_id,
                    r.transaction_id,
                    r.customer_id,
                    r.transaction_date,
                    r.transaction_type,
                    r.amount,
                    r.currency,
                    r.payment_method,
                    r.status
                FROM raw.transactions r
                WHERE r.run_id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM staging.transactions s
                      WHERE s.raw_id = r.raw_id
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM ops.pipeline_errors e
                      WHERE e.raw_id = r.raw_id
                  )
                ORDER BY r.raw_id
                """,
                (run_id,),
            )

            raw_records = cursor.fetchall()

            staging_records = []
            error_records = []

            for row in raw_records:
                (
                    raw_id,
                    record_run_id,
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    payment_method,
                    status,
                ) = row

                raw_record = {
                    "transaction_id": transaction_id,
                    "customer_id": customer_id,
                    "transaction_date": transaction_date,
                    "transaction_type": transaction_type,
                    "amount": amount,
                    "currency": currency,
                    "payment_method": payment_method,
                    "status": status,
                }

                standardized, errors = validate_record(raw_record)

                if errors:
                    for error in errors:
                        error_records.append(
                            (
                                record_run_id,
                                raw_id,
                                transaction_id,
                                error,
                            )
                        )

                else:
                    staging_records.append(
                        (
                            standardized["transaction_id"],
                            standardized["customer_id"],
                            standardized["transaction_date"],
                            standardized["transaction_type"],
                            standardized["amount"],
                            standardized["currency"],
                            standardized["payment_method"],
                            standardized["status"],
                            raw_id,
                            record_run_id,
                        )
                    )

            if staging_records:
                cursor.executemany(
                    """
                    INSERT INTO staging.transactions (
                        transaction_id,
                        customer_id,
                        transaction_date,
                        transaction_type,
                        amount,
                        currency,
                        payment_method,
                        status,
                        raw_id,
                        run_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    staging_records,
                )

            if error_records:
                cursor.executemany(
                    """
                    INSERT INTO ops.pipeline_errors (
                        run_id,
                        raw_id,
                        transaction_id,
                        error_reason
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    error_records,
                )

            # Recalculate counts for this pipeline run.
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM staging.transactions
                WHERE run_id = %s
                """,
                (run_id,),
            )

            records_loaded = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(DISTINCT raw_id)
                FROM ops.pipeline_errors
                WHERE run_id = %s
                """,
                (run_id,),
            )

            records_rejected = cursor.fetchone()[0]

            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET records_loaded = %s,
                    records_rejected = %s
                WHERE run_id = %s
                """,
                (records_loaded, records_rejected, run_id),
            )

    print("TRANSACTION VALIDATION COMPLETED")
    print("--------------------------------")
    print(f"Pipeline run ID: {run_id}")
    print(f"Records examined: {len(raw_records)}")
    print(f"Valid records staged: {len(staging_records)}")
    print(f"Rejected records: {len({
        record[1] for record in error_records
    })}")
    print(f"Validation errors recorded: {len(error_records)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate raw financial transactions."
    )

    parser.add_argument(
        "--run-id",
        type=int,
        required=True,
        help="Pipeline run ID to validate.",
    )

    arguments = parser.parse_args()

    validate_transactions(arguments.run_id)