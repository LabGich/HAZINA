
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime

from hazina_pipeline.database.connection import get_database_connection


ALLOWED_TRANSACTION_TYPES = {
    "PAYMENT",
    "DEPOSIT",
    "WITHDRAWAL",
    "TRANSFER",
    "REFUND",
    "FEE",
    "REVERSAL",
}

ALLOWED_DIRECTIONS = {
    "DEBIT",
    "CREDIT",
    "UNKNOWN",
}

ALLOWED_PAYMENT_METHODS = {
    "MPESA",
    "BANK_TRANSFER",
    "CARD",
    "CASH",
    "DIGITAL_WALLET",
    "USSD",
    "AGENT",
    "OTHER",
    "UNKNOWN",
}

ALLOWED_STATUSES = {
    "INITIATED",
    "PENDING",
    "COMPLETED",
    "FAILED",
    "REVERSED",
}


def _validate_record(record):
    errors = []

    (
        staging_id,
        raw_id,
        transaction_id,
        transaction_date,
        transaction_type,
        amount,
        currency,
        direction,
        payment_method,
        status,
        fee_amount,
        account_balance,
    ) = record

    def add_error(field_name, error_code, message):
        errors.append({
            "field_name": field_name,
            "error_code": error_code,
            "error_message": message,
        })

    if not isinstance(transaction_id, str) or not transaction_id.strip():
        add_error(
            "transaction_id",
            "INVALID_TRANSACTION_ID",
            "Transaction ID must not be empty.",
        )

    if not isinstance(transaction_date, datetime):
        add_error(
            "transaction_date",
            "INVALID_TRANSACTION_DATE",
            "Transaction date must be a datetime value.",
        )
    elif (
        transaction_date.tzinfo is None
        or transaction_date.utcoffset() is None
    ):
        add_error(
            "transaction_date",
            "TIMEZONE_REQUIRED",
            "Transaction date must include timezone information.",
        )

    if transaction_type not in ALLOWED_TRANSACTION_TYPES:
        add_error(
            "transaction_type",
            "INVALID_TRANSACTION_TYPE",
            f"Unsupported transaction type: {transaction_type!r}.",
        )

    try:
        numeric_amount = Decimal(str(amount))

        if not numeric_amount.is_finite() or numeric_amount <= 0:
            raise ValueError

    except (InvalidOperation, ValueError, TypeError):
        add_error(
            "amount",
            "INVALID_AMOUNT",
            "Transaction amount must be a finite positive number.",
        )

    if (
        not isinstance(currency, str)
        or not re.fullmatch(r"[A-Z]{3}", currency.strip())
    ):
        add_error(
            "currency",
            "INVALID_CURRENCY",
            "Currency must be a three-letter uppercase currency code.",
        )

    if direction not in ALLOWED_DIRECTIONS:
        add_error(
            "direction",
            "INVALID_DIRECTION",
            f"Unsupported transaction direction: {direction!r}.",
        )

    if payment_method not in ALLOWED_PAYMENT_METHODS:
        add_error(
            "payment_method",
            "INVALID_PAYMENT_METHOD",
            f"Unsupported payment method: {payment_method!r}.",
        )

    if status not in ALLOWED_STATUSES:
        add_error(
            "status",
            "INVALID_STATUS",
            f"Unsupported transaction status: {status!r}.",
        )

    if fee_amount is not None:
        try:
            numeric_fee = Decimal(str(fee_amount))

            if not numeric_fee.is_finite() or numeric_fee < 0:
                raise ValueError

        except (InvalidOperation, ValueError, TypeError):
            add_error(
                "fee_amount",
                "INVALID_FEE_AMOUNT",
                "Fee amount must be a finite, non-negative number.",
            )

    if account_balance is not None:
        try:
            numeric_balance = Decimal(str(account_balance))

            if not numeric_balance.is_finite():
                raise ValueError

        except (InvalidOperation, ValueError, TypeError):
            add_error(
                "account_balance",
                "INVALID_ACCOUNT_BALANCE",
                "Account balance must be a finite number.",
            )

    return errors


def validate_source_execution(run_id, source_execution_id):
    if not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("run_id must be a positive integer.")

    if not isinstance(source_execution_id, int) or source_execution_id <= 0:
        raise ValueError(
            "source_execution_id must be a positive integer."
        )

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Confirm and lock the source execution.
            # Organization ownership comes from the parent pipeline run.
            cursor.execute(
                """
                SELECT
                    se.execution_status,
                    pr.organization_id
                FROM ops.source_executions se
                JOIN ops.pipeline_runs pr
                    ON pr.run_id = se.run_id
                WHERE se.run_id = %s
                  AND se.source_execution_id = %s
                FOR UPDATE OF se
                """,
                (run_id, source_execution_id),
            )

            execution = cursor.fetchone()

            if execution is None:
                raise ValueError(
                    "Source execution does not belong to the supplied run."
                )

            execution_status, organization_id = execution

            if execution_status != "RUNNING":
                raise ValueError(
                    "Source execution must be RUNNING before validation."
                )

            # Select only pending staging records owned by this run's
            # organization. IS NOT DISTINCT FROM preserves legacy NULL runs.
            cursor.execute(
                """
                SELECT
                    staging_id,
                    raw_id,
                    transaction_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    direction,
                    payment_method,
                    status,
                    fee_amount,
                    account_balance
                FROM staging.transactions
                WHERE run_id = %s
                  AND source_execution_id = %s
                  AND organization_id IS NOT DISTINCT FROM %s
                  AND validation_status = 'PENDING'
                ORDER BY staging_id
                FOR UPDATE
                """,
                (run_id, source_execution_id, organization_id),
            )

            records = cursor.fetchall()

            records_valid = 0
            records_invalid = 0
            errors_recorded = 0

            for record in records:
                staging_id = record[0]
                raw_id = record[1]
                transaction_id = record[2]

                errors = _validate_record(record)

                if errors:
                    cursor.execute(
                        """
                        UPDATE staging.transactions
                        SET validation_status = 'INVALID'
                        WHERE staging_id = %s
                          AND run_id = %s
                          AND source_execution_id = %s
                          AND organization_id IS NOT DISTINCT FROM %s
                          AND validation_status = 'PENDING'
                        """,
                        (
                            staging_id,
                            run_id,
                            source_execution_id,
                            organization_id,
                        ),
                    )

                    for error in errors:
                        cursor.execute(
                            """
                            INSERT INTO ops.validation_errors (
                                run_id,
                                source_execution_id,
                                staging_id,
                                raw_id,
                                transaction_id,
                                error_code,
                                error_message,
                                field_name
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                run_id,
                                source_execution_id,
                                staging_id,
                                raw_id,
                                transaction_id,
                                error["error_code"],
                                error["error_message"],
                                error["field_name"],
                            ),
                        )

                    records_invalid += 1
                    errors_recorded += len(errors)

                else:
                    cursor.execute(
                        """
                        UPDATE staging.transactions
                        SET validation_status = 'VALID'
                        WHERE staging_id = %s
                          AND run_id = %s
                          AND source_execution_id = %s
                          AND organization_id IS NOT DISTINCT FROM %s
                          AND validation_status = 'PENDING'
                        """,
                        (
                            staging_id,
                            run_id,
                            source_execution_id,
                            organization_id,
                        ),
                    )

                    records_valid += 1

            # Recalculate rejected records:
            # 1. Mapping failures that never reached staging.
            # 2. Staged records that failed validation.
            # All staging checks remain scoped to the execution's organization.
            cursor.execute(
                """
                UPDATE ops.source_executions
                SET records_rejected = (
                    SELECT COUNT(DISTINCT me.raw_id)
                    FROM ops.mapping_errors me
                    WHERE me.run_id = %s
                      AND me.source_execution_id = %s
                      AND me.raw_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM staging.transactions st
                          WHERE st.raw_id = me.raw_id
                            AND st.run_id = %s
                            AND st.source_execution_id = %s
                            AND st.organization_id
                                IS NOT DISTINCT FROM %s
                      )
                ) + (
                    SELECT COUNT(DISTINCT st.raw_id)
                    FROM staging.transactions st
                    WHERE st.run_id = %s
                      AND st.source_execution_id = %s
                      AND st.organization_id IS NOT DISTINCT FROM %s
                      AND st.validation_status = 'INVALID'
                )
                WHERE run_id = %s
                  AND source_execution_id = %s
                """,
                (
                    run_id,
                    source_execution_id,
                    run_id,
                    source_execution_id,
                    organization_id,
                    run_id,
                    source_execution_id,
                    organization_id,
                    run_id,
                    source_execution_id,
                ),
            )

            return {
                "run_id": run_id,
                "source_execution_id": source_execution_id,
                "records_examined": len(records),
                "records_valid": records_valid,
                "records_invalid": records_invalid,
                "errors_recorded": errors_recorded,
            }
